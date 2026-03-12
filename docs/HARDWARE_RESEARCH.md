# Hydrow Hardware Research Log

This document tracks all discoveries about the Hydrow rowing machine hardware interface.

Unknowns should be documented rather than guessed.

---

# Confirmed Facts

| Item            | Status  |
| --------------- | ------- |
| Tablet OS       | Android |
| APK sideloading | Works   |
| Custom launcher | Works   |
| Root required   | No      |

---

# Hardware Interfaces

## 3.5mm Jack

Assumption:

The rowing machine control board sends sensor data through the 3.5mm jack.

Possible formats:

* analog telemetry
* pulse encoding
* serial-over-audio
* frequency encoding

Status: **unknown**

---

# Investigation Plan

## Step 1 — Raw Audio Capture

Capture raw PCM input.

Record:

* sample rate
* amplitude range
* waveform shape

Tools to build:

```
SignalInspectorActivity
```

Displays:

* waveform
* frequency spectrum
* amplitude histogram

---

## Step 2 — Signal Characterization

Questions to answer:

1. Is the signal continuous or burst-based?
2. Does it contain repeating frames?
3. Does frequency change with rowing activity?
4. Does amplitude correlate with stroke force?

---

## Step 3 — Stroke Detection

If signal corresponds to rowing motion:

Possible pattern:

```
stroke start
drive phase
recovery phase
```

Look for periodicity.

---

## Step 4 — Hardware Control Path

Resistance control may occur through:

1. Android service
2. JNI library
3. serial device
4. Bluetooth
5. USB interface

Investigations:

```
adb shell service list
```

Look for vendor services.

---

# Hydrow App Reverse Engineering

Extract Hydrow APK.

Tools:

* jadx
* apktool

Search for keywords:

```
drag
resistance
erg
damper
```

Look for:

```
setDrag()
setResistance()
```

---

# Signals to Record

During rowing tests capture:

```
idle signal
light rowing
heavy rowing
rapid strokes
```

Store recordings in:

```
docs/signal_samples/
```

---

# Important Unknowns

| Unknown                | Priority |
| ---------------------- | -------- |
| Sensor signal encoding | High     |
| Drag control interface | High     |
| Telemetry frame format | Medium   |

---

# Experiment Log

Agents and developers should record experiments here.

Example format:

```
DATE:
TEST:
RESULT:
INTERPRETATION:
```

---

# Example

DATE: 2026-03-10

TEST:
Recorded 30 seconds of audio from jack while rowing.

RESULT:
Signal shows repeating peaks at stroke rate.

INTERPRETATION:
Likely amplitude or pulse encoding.
