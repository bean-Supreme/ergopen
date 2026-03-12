# ergopen

Custom Android launcher and control interface for the rowing machine rowing machine tablet.

This project enables direct access to rowing machine telemetry and hardware controls by running a sideloaded Android app on the rowing machine tablet.

The application is designed to replace (or augment) the stock rowing machine launcher and expose machine controls such as drag/resistance while also providing access to raw sensor data for custom analytics.

---

# Project Status

Early-stage hardware exploration.

Confirmed so far:

* Apps can be **sideloaded** onto the rowing machine tablet
* A **custom launcher can run successfully**
* The environment behaves similarly to a normal Android tablet

Major remaining unknowns:

* Sensor signal format coming from the rowing hardware
* Interface used to control drag/resistance

---

# Goals

Primary goals:

* Read rowing machine telemetry from the hardware board
* Decode rowing metrics from the incoming signal
* Provide UI controls for drag/resistance
* Provide access to Android system controls (volume, brightness, etc.)
* Run as a custom launcher on the rowing machine tablet

Secondary goals:

* Provide diagnostics for reverse engineering hardware signals
* Allow experimentation with rowing analytics
* Provide a platform for custom rowing experiences

---

# Architecture Overview

The project is structured into modular subsystems:

```
sensor      -> hardware signal capture
decoder     -> telemetry decoding
analytics   -> rowing metrics
hardware    -> machine control commands
system      -> android system controls
ui          -> user interface
```

Dependency flow:

```
sensor
  ↓
decoder
  ↓
analytics
  ↓
ui
```

Hardware control is handled separately through the `hardware` module.

---

# Current Focus

Early development is focused on **hardware signal discovery**.

The first major milestone is building tools to inspect the signal coming from the rowing machine.

The primary tool for this is the **Signal Inspector**.

---

# Signal Inspector

The Signal Inspector is a diagnostic activity that reads raw audio data from the **3.5mm jack** and visualizes it.

Capabilities:

* capture raw PCM audio input
* display waveform
* compute amplitude statistics
* inspect frequency spectrum
* record samples for offline analysis

This tool helps determine how the rowing machine encodes telemetry.

More details:

```
docs/SIGNAL_INSPECTOR.md
```

---

# Hardware Assumptions

Current working assumptions:

* The rowing machine control board transmits telemetry through the **3.5mm audio jack**
* The signal likely appears as an **audio waveform**
* Telemetry may be encoded using:

  * analog amplitude
  * pulse encoding
  * frequency encoding
  * serial-over-audio

These assumptions must be verified experimentally.

---

# Development Setup

Requirements:

* Android Studio
* ADB access to the rowing machine tablet
* Ability to sideload APKs

Example install workflow:

```
adb connect <tablet-ip>
adb install ergopen.apk
```

---

# Repository Structure

```
ergopen
│
├── app
│   ├── sensor
│   ├── decoder
│   ├── analytics
│   ├── hardware
│   ├── system
│   └── ui
│
├── docs
│   ├── HARDWARE_RESEARCH.md
│   ├── SIGNAL_INSPECTOR.md
│
├── tools
│   └── signal_inspector
│
├── AGENTS.md
└── README.md
```

---

# Development Milestones

Milestone 1
Capture raw sensor signal from audio jack.

Milestone 2
Characterize signal and determine encoding.

Milestone 3
Prototype telemetry decoder.

Milestone 4
Implement drag/resistance control.

Milestone 5
Build rowing control UI.

Milestone 6
Launcher integration.

---

# Safety

This project interacts with rowing machine hardware.

All hardware control must enforce safe limits.

Example:

```
drag ∈ [50, 200]
```

Invalid values should never be sent to hardware.

---

# Research Documentation

All hardware discoveries should be logged in:

```
docs/HARDWARE_RESEARCH.md
```

Signal recordings should be stored in:

```
docs/signal_samples/
```

---

# Contributing

Before implementing hardware features:

1. Capture raw signal data
2. Inspect waveform
3. Log observations
4. Document experiments

Avoid making assumptions about hardware behavior without recorded data.

---

# License

TBD

---

# Disclaimer

This project is an independent experiment and is not affiliated with or endorsed by rowing machine.
