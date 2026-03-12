# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

# Project Summary

**hydropen** is a custom Android launcher and control interface for the rowing machine rowing machine tablet. It reads sensor telemetry from the rowing machine hardware, decodes rowing metrics, and provides UI controls for drag/resistance and Android system settings.

Current status: early-stage hardware exploration. Signal encoding and hardware control interface are still unknown.

---

# Development Setup

- Android Studio + ADB access to the rowing machine tablet
- Root access is **not required** and should not be assumed

```bash
adb connect <tablet-ip>
adb install ergopen.apk
```

No build scripts exist yet — Android project scaffolding must be created as part of setup.

---

# Architecture

Five loosely-coupled subsystems with a strict dependency flow:

```
sensor      -> hardware signal capture (3.5mm audio jack, PCM 44100 Hz, 16-bit mono)
  ↓
decoder     -> telemetry decoding (encoding format TBD via experimentation)
  ↓
analytics   -> rowing metrics calculation
  ↓
ui          -> user interface (Jetpack Compose)

hardware    -> machine control commands (separate subsystem, drag ∈ [50, 200])
system      -> Android system controls (volume, brightness)
```

The decoder must **never** depend on ui. Hardware and system subsystems are independent of the data pipeline.

Language: Kotlin. Architecture pattern: MVVM or modular service architecture.

---

# Development Priorities

1. Sensor capture from 3.5mm audio jack
2. Signal inspection and decoding tools
3. Drag/resistance control
4. User interface
5. Launcher integration

---

# Key Rules

**Instrumentation over speculation** — when hardware behavior is unknown, build tools to inspect it (signal visualizers, loggers, packet inspectors). Never hardcode interpretations before data confirms them.

**Hardware logging** — all hardware interactions must log: timestamp, source, raw data, decoded value.

**Safety** — hardware control must enforce bounds. Never send unbounded values to hardware interfaces.

**Do not:**
- Assume undocumented hardware protocols
- Remove diagnostic logging
- Merge hardware and UI logic
- Implement speculative decoding algorithms without data

---

# Testing Strategy

Hardware cannot be tested automatically. Use simulation layers:

```kotlin
FakeSensorSource
MockTelemetry
SimulatedStrokeStream
```

---

# Research Documentation

- Hardware discoveries → `docs/HARDWARE_RESEARCH.md`
- Signal Inspector spec → `docs/SIGNAL_INSPECTOR.md`
- Signal recordings → `docs/signal_samples/`

Before implementing any hardware feature: capture raw signal → inspect waveform → log observations → document experiments.
