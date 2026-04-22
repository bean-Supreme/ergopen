# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

---

## Project Summary

**ergopen** is a local web app that reads the Hydrow rowing machine's flywheel sensor signal via a laptop's 3.5mm audio jack and displays real-time rowing metrics (split, SPM, watts, RPM).

The Hydrow control board sends an analog sinusoidal signal on the 3.5mm cable (alongside UART serial). We read it via the laptop mic input — no root, no Android involvement.

---

## Stack

| Layer    | Technology                                         |
|----------|----------------------------------------------------|
| Backend  | Python, FastAPI, sounddevice, numpy                |
| Frontend | Vite, React, TypeScript, Tailwind v4, recharts     |
| Comms    | WebSocket at `ws://localhost:8000/stream`, ~20 fps |

---

## Running

```bash
# Backend
uvicorn server.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev
```

---

## Architecture

```
server/main.py       FastAPI app + WebSocket broadcast loop
server/capture.py    AudioCapture (live mic or .pcm replay)
server/analysis.py   pitch detection, FFT, stroke detection, split formula
server/models.py     Pydantic models — SignalFrame is the main broadcast type
server/types.ts      TypeScript mirror of models.py — keep in sync manually

frontend/src/pages/Dashboard.tsx        / — split (hero), SPM, watts, RPM
frontend/src/pages/Debug.tsx            /debug — waveform, FFT, readouts, capture controls
frontend/src/lib/ergopen/useStream.ts   WebSocket hook
frontend/src/lib/ergopen/types.ts       TypeScript types (mirror of server/types.ts)

inspector/inspector.py   Standalone matplotlib inspector (no server needed)
signal_captures/*.pcm    Raw recordings, 16-bit mono PCM at 44100 Hz
```

---

## Key constants (server/analysis.py)

```python
SAMPLE_RATE    = 44100
NOISE_FLOOR    = 170
ACTIVE_THRESH  = 500
POWER_K        = 4.0   # uncalibrated: watts = K * rps³
# PULSES_PER_REV = 48  # set in Config (default 48, best candidate — unverified)
```

Split formula: `500 * (2.8 / watts) ** (1/3)` seconds per 500m.

---

## Signal facts

- Inductive pickup coil on flywheel, ~100–400 Hz during rowing
- Clean sinusoid — no harmonics, no digital edges
- Optimal mic gain: ~40% (avoids clipping, maintains SNR)
- Autocorrelation pitch detection (ACF via FFT), EMA smoothed (α=0.15)
- Stroke detection: frequency valley transitions → drive-start counts

---

## Key rules

**Keep `server/types.ts` and `frontend/src/lib/ergopen/types.ts` in sync** — they are manual mirrors of `server/models.py`. When `SignalFrame` changes, update all three.

**`analyze()` is pure** — `StrokeDetector` is stateful and lives in `_State` in `main.py`.

**Instrumentation over speculation** — build inspection tools before assuming signal behavior.

---

## Research documentation

- Hardware discoveries → `docs/HARDWARE_RESEARCH.md`
- Signal recordings → `signal_captures/`

---

## Android archive

Original Android launcher concept is in `archive/android/`. Superseded — do not modify.
