# ergopen

A local web app that reads the Hydrow rowing machine's flywheel sensor via a laptop's 3.5mm audio jack and displays real-time rowing metrics.

---

## How it works

The Hydrow control board sends an analog sinusoidal signal over the 3.5mm cable (alongside UART serial on the same connector). With the laptop mic input, we can read this signal directly — no root, no Android, no proprietary protocol.

```
flywheel magnets → inductive pickup coil → 3.5mm cable → laptop mic input
                                                               ↓
                                                  FastAPI + sounddevice
                                                               ↓
                                              autocorrelation pitch detection
                                                               ↓
                                              Vite + React dashboard (WebSocket)
```

Signal frequency tracks flywheel RPM. Stroke shape (rising/falling frequency envelope) drives stroke detection and SPM.

---

## Running

**Backend**

```bash
cd server
pip install -r requirements.txt
uvicorn server.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` for the dashboard, `/debug` for raw signal inspection.

---

## Architecture

```
server/
  main.py       FastAPI app, WebSocket broadcast loop (~20 fps)
  capture.py    AudioCapture — live mic or .pcm file replay
  analysis.py   Signal analysis: pitch detection, FFT, stroke detection, split
  models.py     Pydantic models (SignalFrame, Config, ...)
  types.ts      TypeScript mirror of models.py — keep in sync manually

frontend/src/
  pages/
    Dashboard.tsx   / — split, SPM, watts, RPM
    Debug.tsx       /debug — waveform, FFT, digital readouts, capture controls
  components/
    WaveformCanvas.tsx   Canvas-based waveform (ResizeObserver)
    FftChart.tsx         Recharts AreaChart (50–600 Hz)
  lib/ergopen/
    useStream.ts    WebSocket hook, auto-reconnect
    types.ts        TypeScript types (mirror of server/types.ts)

inspector/
  inspector.py    Standalone matplotlib inspector (no server needed)

signal_captures/
  *.pcm           Raw 16-bit mono PCM recordings at 44100 Hz
```

---

## Signal facts

| Property              | Value                                       |
|-----------------------|---------------------------------------------|
| Type                  | Clean sinusoid (inductive pickup coil)      |
| Frequency at idle     | < 50 Hz (below detection range)             |
| Frequency range       | ~100–400 Hz during active rowing            |
| Noise floor (RMS)     | < 170                                       |
| Active threshold      | RMS > 500                                   |
| Sample rate           | 44100 Hz, 16-bit mono                       |
| Mic gain (optimal)    | ~40% — avoids clipping, good SNR            |
| Pulses per rev        | 48 (best candidate — physically unverified) |
| Power constant K      | 4.0 (uncalibrated)                          |

Formulas:

```
rps   = freq_hz / PULSES_PER_REV
rpm   = rps * 60
watts = K * rps³
split = 500 * (2.8 / watts)^(1/3)   # seconds per 500m
```

---

## Hardware research

All findings documented in `docs/HARDWARE_RESEARCH.md`.

The UART serial protocol (baud 921600, `Di`/`Ds` packets) was fully reverse-engineered from the stock APK, but `/dev/ttyS1` is inaccessible without root. The audio path is the active approach.

**Next hardware step:** open flywheel cover to physically count magnets and confirm `PULSES_PER_REV`.

---

## Archive

Original Android launcher concept is in `archive/android/`. Superseded by this approach.
