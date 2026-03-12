# AGENTS.md

This repository is designed to be worked on by both humans and AI coding agents.

Agents should read this file before making changes.

---

# Project Summary

This project implements a **custom Android application for rowing machine tablets**.

The app will:

1. Run as a **custom launcher**
2. Read **sensor telemetry from the rowing machine hardware**
3. Provide UI controls for **drag/resistance**
4. Provide UI controls for **Android system settings** (volume, brightness, etc.)

The device supports **APK sideloading**, and a custom launcher has already been successfully installed.

Root access is **not required** and should not be assumed.

---

# Key Architectural Principle

The project is divided into **five major subsystems**.

Agents should maintain this separation.

```
sensor      -> hardware signal capture
decoder     -> telemetry decoding
analytics   -> rowing metrics
hardware    -> machine control commands
ui          -> user interface
```

Each subsystem must remain **loosely coupled**.

Communication between subsystems should occur through clearly defined interfaces.

---

# Development Priorities

Agents should focus on tasks in this order:

### Priority 1

Sensor capture from the **3.5mm audio jack**

### Priority 2

Signal inspection and decoding tools

### Priority 3

Drag/resistance control

### Priority 4

User interface

### Priority 5

Launcher integration

---

# Hardware Assumptions

Current assumptions:

* Rowing machine tablet runs Android
* Apps can be sideloaded
* Launcher replacement works
* Rowing machine sensor data enters via **3.5mm jack**
* Sensor signal likely appears as **audio waveform input**

These assumptions must **not be treated as guaranteed facts**.

Agents should prefer **instrumentation and diagnostics** over speculation.

---

# Agent Guidelines

## Prefer Instrumentation

When hardware behavior is unknown, create tools to inspect it.

Examples:

* raw signal visualizer
* logging tools
* packet inspectors
* telemetry dump utilities

Avoid hardcoding interpretations until data confirms them.

---

# Avoid Tight Coupling

The decoder must **not depend on UI code**.

Correct dependency flow:

```
sensor
  ↓
decoder
  ↓
analytics
  ↓
ui
```

---

# Safe Hardware Control

The app may control rowing machine resistance.

Agents must enforce safety limits.

Example:

```
drag level ∈ [50, 200]
```

Never send unbounded values to hardware interfaces.

---

# Code Style

Preferred language: **Kotlin**

Architecture:

* MVVM or modular service architecture
* Jetpack Compose for UI

Avoid large monolithic classes.

---

# Testing Strategy

Hardware is difficult to test automatically.

Agents should implement:

### Simulation layers

Example:

```
FakeSensorSource
MockTelemetry
SimulatedStrokeStream
```

This allows development without the rowing machine.

---

# Logging Requirements

All hardware interaction must log:

```
timestamp
source
raw data
decoded value
```

Logs are critical for reverse engineering.

---

# Repository Structure

```
app/
  sensor/
  decoder/
  analytics/
  hardware/
  system/
  ui/

docs/
  hardware_research.md
  signal_analysis.md

tools/
  signal_inspector/
```

Agents should keep code in the appropriate module.

---

# Things Agents Must NOT Do

Do not:

* assume undocumented hardware protocols
* remove diagnostic logging
* merge hardware and UI logic
* implement speculative decoding algorithms without data

---

# When Hardware Behavior Is Unknown

Agents should:

1. Capture raw data
2. Visualize signal
3. Log samples
4. Build decoding experiments

Never skip step 1.
