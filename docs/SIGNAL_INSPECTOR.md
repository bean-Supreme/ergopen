# Signal Inspector

The Signal Inspector is a diagnostic tool used to analyze the signal coming from the rowing machine via the **3.5mm audio jack**.

This tool is critical for reverse engineering the telemetry format.

It allows developers and AI agents to:

* visualize the raw waveform
* inspect amplitude levels
* inspect frequency spectrum
* record sample data for offline analysis

---

# Purpose

The rowing machine control board likely sends telemetry through the audio input channel.

Possible encodings include:

* analog voltage level
* pulse width modulation
* frequency modulation
* serial-over-audio

The Signal Inspector allows us to determine which encoding is used.

---

# Features

## Real-time waveform display

Displays incoming PCM data in real time.

Useful for identifying:

* pulse patterns
* stroke cycles
* amplitude changes

---

## FFT Spectrum

Displays frequency components of the signal.

Useful for detecting:

* frequency encoded telemetry
* carrier signals
* modulated data

---

## Signal Statistics

Display:

* min amplitude
* max amplitude
* RMS level

---

## Recording

Allow recording short sessions for later analysis.

Recordings stored at:

```
/docs/signal_samples/
```

Recommended capture scenarios:

1. idle machine
2. light rowing
3. heavy rowing
4. fast stroke rate

---

# UI Layout

Example screen:

```
----------------------------------
ergopen Signal Inspector

Waveform
██████████░░░░░░██████░░░░

Frequency Spectrum
|    |  |    ||      | |

Amplitude
Min: -2100
Max: 2300
RMS: 840

[Start] [Stop] [Record]
----------------------------------
```

---

# Implementation Notes

Android API used:

```
AudioRecord
```

Recommended configuration:

```
sampleRate: 44100
encoding: PCM_16BIT
channel: MONO
buffer: 2048 samples
```

---

# Important

The inspector must **never attempt to interpret the signal automatically**.

Its purpose is to **observe and record raw data**, not decode it.

Decoding belongs in the `decoder` module.

---

# Output Data Format

Recording files should be saved as:

```
.raw
```

Format:

```
16-bit PCM
44100Hz
mono
```

This format can be inspected with tools like:

* Audacity
* Python numpy
* MATLAB
