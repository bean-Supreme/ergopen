# AGENTS.md

This repository is designed to be worked on by both humans and AI coding agents.

Agents should read this file before making changes.

---

## Project Summary

**ergopen** is a local web app that reads the Hydrow rowing machine's flywheel sensor
signal via a laptop's 3.5mm audio jack and displays real-time rowing metrics
(split, SPM, watts, RPM).

The Hydrow control board sends an analog sinusoidal signal on the 3.5mm cable
(alongside UART serial). We read it via the laptop mic input — no root, no Android
involvement.

The original Android-launcher approach is archived under `archive/android/` and
must not be modified. See `docs/HARDWARE_RESEARCH.md` for the pivot rationale.

---

## Stack

| Layer    | Technology                                         |
|----------|----------------------------------------------------|
| Backend  | Python, FastAPI, sounddevice, numpy                |
| Frontend | Vite, React, TypeScript, Tailwind v4, recharts     |
| Comms    | WebSocket at `ws://localhost:8000/stream`, ~20 fps |

---

## Repository Structure

```
server/              FastAPI backend
  main.py            app + WebSocket broadcast loop
  capture.py         AudioCapture (live mic or .pcm replay)
  analysis.py        pitch detection, FFT, stroke detection, split
  models.py          Pydantic models (SignalFrame is the main broadcast type)
  types.ts           TypeScript mirror of models.py — keep in sync manually

frontend/src/
  pages/             Dashboard.tsx (/), Debug.tsx (/debug)
  components/        WaveformCanvas, FftChart, ...
  lib/ergopen/       useStream.ts (WebSocket hook), types.ts

inspector/           Standalone matplotlib inspector (no server needed)
signal_captures/     Raw recordings, 16-bit mono PCM at 44100 Hz
tools/               Offline calibration utilities
docs/                Hardware research + signal inspector docs
archive/android/     Archived Android launcher — do not modify
apks/                Decompiled stock APKs — research reference, gitignored
```

---

## Running

```bash
# Backend — run from repo root, not from inside server/
uvicorn server.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# Open http://localhost:5173 for the dashboard, /debug for raw signal inspection
```

---

## Agent Guidelines

### Prefer instrumentation

When signal behavior is unknown, build inspection tools before assuming. The
`inspector/` tool and `/debug` page already exist for this — extend them rather
than speculating from code alone. Avoid hardcoding interpretations until data
confirms them.

### Keep the type mirror in sync

`server/models.py`, `server/types.ts`, and `frontend/src/lib/ergopen/types.ts`
are manual mirrors. When `SignalFrame` or any shared model changes, update all
three — out-of-sync types will silently break the WebSocket contract.

### Preserve the pure/stateful split

`analyze()` in `server/analysis.py` is pure — it takes samples and returns a dict.
`StrokeDetector` is stateful and lives in `_State` in `server/main.py`. Don't
merge them; don't introduce module-level state in `analysis.py`.

### Loose coupling

Dependency direction:

```
capture → analysis → broadcast → frontend
```

Frontend must not reach into server internals. Analysis code must not depend on
transport (WebSocket, HTTP). Capture must not know about analysis.

### Safe hardware control

If a future path exposes the rowing machine's drag/resistance (via root, a new
interface, or user-supplied hardware), the drag level MUST be clamped to
`[50, 200]`. Never send unbounded values to hardware interfaces. The UART
command set is documented in `docs/HARDWARE_RESEARCH.md`.

### Logging

Hardware-adjacent code should log enough context to reverse-engineer behavior
later — at minimum `timestamp`, `source`, and the raw values being interpreted.
Don't remove diagnostic logging to make output "cleaner".

### Testing hardware-dependent code

Hardware is difficult to test automatically. Use `.pcm` replay (`inspector/inspector.py <file>`
or `POST /replay`) to feed recorded signals through the pipeline. When adding
new analysis behavior, capture a session that exercises it and keep it under
`signal_captures/` (gitignored, but shareable).

---

## Calibration Status

Two physical constants gate the accuracy of every displayed metric:

| Constant          | Current value | Status                                            |
|-------------------|---------------|---------------------------------------------------|
| `PULSES_PER_REV`  | 48            | Best guess — needs physical magnet count          |
| `POWER_K`         | 4.0           | Uncalibrated — needs known-load or UART reference |

Changing either affects RPM, watts, and split proportionally. Treat them as
hypotheses, not facts.

---

## Things Agents Must NOT Do

- Assume undocumented hardware protocols
- Remove diagnostic logging
- Merge analysis and UI/transport logic
- Implement speculative decoding algorithms without data
- Modify anything under `archive/android/` — it is frozen research
- Update one of the three type-mirror files without updating all three
