# Signal Inspector

Tools for inspecting the raw analog flywheel signal from the Hydrow rowing machine.

Two interfaces exist — the standalone inspector for quick offline analysis, and the web debug dashboard for live inspection.

---

## Standalone inspector (`inspector/inspector.py`)

Matplotlib-based tool. No server required. Works on recorded `.pcm` files or live mic input.

```bash
python inspector/inspector.py signal_captures/signal_XXXXX.pcm
```

Shows:
- Raw waveform (time domain)
- FFT spectrum (50–600 Hz)
- RMS and peak amplitude
- Detected frequency (autocorrelation)

---

## Web debug dashboard (`/debug`)

Live inspection via the FastAPI + React app.

```bash
uvicorn server.main:app --reload --port 8000
cd frontend && npm run dev
# open http://localhost:5173/debug
```

Shows:
- Real-time waveform (canvas, last ~100ms)
- Live FFT spectrum (50–600 Hz, recharts)
- Digital readouts: RMS, freq, RPM, watts, PPR, active state
- Capture start/stop and recording controls

---

## Recording format

Files saved to `signal_captures/`:

```
filename:    signal_<unix_ms>.pcm
encoding:    16-bit signed PCM, little-endian
sample rate: 44100 Hz
channels:    mono
```

Compatible with Audacity (raw import), numpy (`np.frombuffer(..., dtype=np.int16)`), and the replay endpoint (`POST /replay`).

---

## Recommended capture scenarios

1. Machine idle (establishes noise floor)
2. Light rowing, steady pace
3. Hard rowing at high SPM
4. Spin-down from peak to rest

---

## Signal interpretation status

| Property            | Status             | Value / Notes                                  |
|---------------------|--------------------|------------------------------------------------|
| Signal type         | Confirmed          | Inductive pickup coil, clean sinusoid          |
| Frequency range     | Confirmed          | ~100–400 Hz during rowing                      |
| Noise floor         | Confirmed          | RMS < 170                                      |
| Active threshold    | Confirmed          | RMS > 500                                      |
| Freq → RPM mapping  | Working            | `rps = freq / PPR`, `rpm = rps * 60`           |
| Pulses per rev      | Unverified         | 48 (best candidate — needs physical inspection)|
| Power constant K    | Uncalibrated       | `watts = 4.0 * rps³`                           |
| Stroke detection    | Working            | Valley-to-rise transitions on EMA freq         |
| Split calculation   | Working            | `500 * (2.8 / watts)^(1/3)` sec/500m          |
