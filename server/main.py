"""
ergopen backend — FastAPI + WebSocket

Start:
  uvicorn server.main:app --reload --port 8000

WebSocket:
  ws://localhost:8000/stream

REST:
  GET  /devices
  GET  /config
  POST /config
  POST /capture/start
  POST /capture/stop
  POST /record/start
  POST /record/stop
  GET  /recordings
  POST /replay
"""

import asyncio
import logging
import struct
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .analysis import analyze, FFT_FREQS, StrokeDetector, split_from_watts
from .capture import AudioCapture
from .models import (
    Config, ConfigUpdate, DeviceInfo, RecordingInfo,
    ReplayRequest, SignalFrame,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

CAPTURES_DIR = Path(__file__).parent.parent / 'signal_captures'
CAPTURES_DIR.mkdir(exist_ok=True)

BROADCAST_HZ = 20   # frames per second


# ── App state ──────────────────────────────────────────────────────────────────

class _State:
    capture:          AudioCapture
    config:           Config
    ema_freq:         float | None
    stroke_detector:  StrokeDetector
    clients:          list[WebSocket]

state = _State()


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    state.config           = Config()
    state.ema_freq         = None
    state.stroke_detector  = StrokeDetector()
    state.clients          = []
    state.capture  = AudioCapture(device=state.config.device,
                                  sample_rate=state.config.sample_rate)
    # Start the broadcast loop
    task = asyncio.create_task(_broadcast_loop())
    log.info('ergopen backend ready — ws://localhost:8000/stream')
    yield
    task.cancel()
    state.capture.shutdown()


app = FastAPI(title='ergopen', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)


# ── Broadcast loop ─────────────────────────────────────────────────────────────

async def _broadcast_loop() -> None:
    interval = 1 / BROADCAST_HZ
    while True:
        await asyncio.sleep(interval)
        if not state.clients:
            continue

        samples = await asyncio.get_event_loop().run_in_executor(
            None, state.capture.get_samples
        )

        result = analyze(samples, state.config.ppr, state.ema_freq)
        state.ema_freq = result['ema_freq']
        spm       = state.stroke_detector.update(result['freq'])
        split_sec = split_from_watts(result['watts']) if result['watts'] else None

        frame = SignalFrame(
            ts           = time.time(),
            rms          = result['rms'],
            freq         = result['freq'],
            rpm          = result['rpm'],
            watts        = result['watts'],
            waveform     = result['waveform'],
            fft_freqs    = result['fft_freqs'],
            fft_mag      = result['fft_mag'],
            is_active    = result['is_active'],
            is_recording = state.capture.is_recording,
            rec_duration = state.capture.rec_duration,
            spm          = spm,
            split_sec    = split_sec,
        )

        payload = {'type': 'frame', 'data': frame.model_dump()}
        dead    = []
        for ws in list(state.clients):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            state.clients.remove(ws)


# ── WebSocket ──────────────────────────────────────────────────────────────────

@app.websocket('/stream')
async def stream(ws: WebSocket) -> None:
    await ws.accept()
    state.clients.append(ws)
    log.info(f'WebSocket connected  (total: {len(state.clients)})')
    try:
        # Send static FFT frequency axis once on connect
        await ws.send_json({'type': 'init', 'fft_freqs': FFT_FREQS,
                            'config': state.config.model_dump()})
        # Keep connection alive; broadcast loop handles outbound frames
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        state.clients.remove(ws)
        log.info(f'WebSocket disconnected (total: {len(state.clients)})')


# ── Devices ────────────────────────────────────────────────────────────────────

@app.get('/devices', response_model=list[DeviceInfo])
def list_devices() -> list[DeviceInfo]:
    import sounddevice as sd
    devices = sd.query_devices()
    return [
        DeviceInfo(
            index=i,
            name=d['name'],
            max_input_channels=d['max_input_channels'],
            default_samplerate=d['default_samplerate'],
        )
        for i, d in enumerate(devices)
        if d['max_input_channels'] > 0
    ]


# ── Config ─────────────────────────────────────────────────────────────────────

@app.get('/config', response_model=Config)
def get_config() -> Config:
    return state.config


@app.post('/config', response_model=Config)
def update_config(body: ConfigUpdate) -> Config:
    if body.ppr is not None:
        state.config.ppr = body.ppr
        state.ema_freq   = None   # reset EMA on PPR change
    if body.device is not None:
        state.config.device = body.device
    return state.config


# ── Capture control ────────────────────────────────────────────────────────────

@app.post('/capture/start')
def capture_start() -> dict:
    """Start live capture from the configured audio device."""
    try:
        state.capture.start_live()
        return {'status': 'capturing', 'device': state.config.device}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/capture/stop')
def capture_stop() -> dict:
    state.capture.stop_live()
    return {'status': 'stopped'}


# ── Recording ──────────────────────────────────────────────────────────────────

@app.post('/record/start')
def record_start() -> dict:
    state.capture.start_recording()
    return {'status': 'recording'}


@app.post('/record/stop', response_model=RecordingInfo)
def record_stop() -> RecordingInfo:
    samples = state.capture.stop_recording()
    if not samples:
        raise HTTPException(status_code=400, detail='No samples recorded')

    import numpy as np
    ts       = int(time.time() * 1000)
    filename = f'signal_{ts}.pcm'
    path     = CAPTURES_DIR / filename

    ints = np.clip(np.array(samples), -32768, 32767).astype(np.int16)
    path.write_bytes(struct.pack(f'<{len(ints)}h', *ints))

    return RecordingInfo(
        filename   = filename,
        duration_s = len(samples) / state.config.sample_rate,
        size_bytes = path.stat().st_size,
    )


@app.get('/recordings', response_model=list[RecordingInfo])
def list_recordings() -> list[RecordingInfo]:
    result = []
    for p in sorted(CAPTURES_DIR.glob('*.pcm')):
        size      = p.stat().st_size
        n_samples = size // 2
        result.append(RecordingInfo(
            filename   = p.name,
            duration_s = n_samples / state.config.sample_rate,
            size_bytes = size,
        ))
    return result


# ── Replay ─────────────────────────────────────────────────────────────────────

@app.post('/replay')
def replay(body: ReplayRequest) -> dict:
    """Feed a saved .pcm file into the signal pipeline as if it were live."""
    path = CAPTURES_DIR / body.filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f'{body.filename} not found')

    state.capture.start_replay(path)
    return {'status': 'replaying', 'filename': body.filename}
