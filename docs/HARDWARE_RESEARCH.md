# Hardware Research Log

---

## Device

| Item            | Value                        |
|-----------------|------------------------------|
| Model           | `foenix_h`                   |
| SoC             | MediaTek MT8167 (`alps`)     |
| Android         | 10 (SDK 29)                  |
| Resolution      | 1920x1080 landscape          |
| MAC             | 34:E1:D1:C0:C8:5D            |
| ADB             | port 5555, over Wi-Fi/LAN    |

---

## Confirmed Facts

| Item                  | Status    |
|-----------------------|-----------|
| Tablet OS             | Android 10|
| APK sideloading       | Works     |
| Custom launcher       | Works     |
| Root required         | No        |
| ADB over Wi-Fi        | Works     |
| Sensor via 3.5mm jack | **WRONG** — it's UART |

---

## Hardware Interface — CONFIRMED: UART Serial

The rowing machine control board communicates over a **hardware UART**, not audio.

### Device node

```
/dev/ttyMT1  ->  /dev/ttyS1   (symlink)
crw-rw----  system  system
```

`ttyMT1` = MediaTek hardware UART 1.

### Connection parameters

| Parameter | Value    |
|-----------|----------|
| Baud rate | 921600   |
| Parity    | none     |
| Format    | ASCII, space-delimited, `\n\r` terminated |

### Device path search order (from stock APK source)

1. `/dev/ttyACM0`
2. `/dev/ttyMT1`  ← present on this device
3. `/dev/ttyUSB0`

---

## Protocol — CONFIRMED (reverse-engineered from com.truerowing.crew APK)

### Commands (tablet → brake controller)

| Command              | Response prefix | Description                      |
|----------------------|-----------------|----------------------------------|
| `Cm 1\n\r`           | `Rm`            | Enable continuous streaming mode |
| `Cm 0\n\r`           | `Rm`            | Disable continuous streaming mode|
| `Cl <level>\n\r`     | `Rl <level>`    | Set resistance level             |
| `Ql\n\r`             | `Rl`            | Query current resistance level   |
| `Ch\n\r`             | `Rh`            | Report health                    |
| `Cs\n\r`             | `Rs`            | Report serial number             |
| `Cv\n\r`             | `Rv`            | Report firmware version          |
| `Cr\n\r`             | `Rr`            | Soft reboot                      |
| `Qc\n\r`             | `Rc`            | Query resistance curve params    |
| `Cc <...>\n\r`       | `Rc`            | Update resistance curve params   |
| `T1\n\r`             | `t1`            | Start canned (test) data         |
| `T0\n\r`             | `t0`            | Stop canned data                 |

### Streaming packets (received when Cm 1 active)

#### Instantaneous — `Di` (sent at high frequency)

```
Di <rpm5> <revolutions100> <watts10> <handleMM> <sequence>
```

| Field            | Scale | Unit        |
|------------------|-------|-------------|
| rpm5             | ÷ 5   | RPM         |
| revolutions100   | ÷ 100 | revolutions |
| watts10          | ÷ 10  | watts       |
| handleMM         | raw   | millimeters |
| sequence         | raw   | counter     |

Also: `Di2` (V2 variant, same format)

#### Stroke summary — `Ds` (once per stroke)

```
Ds <startPos> <endPos> <driveRev10> <recoveryRev10> <avgWatts10> <lastRecoveryEndIdx> <driveEndIdx> <sequence>
```

| Field                      | Scale | Unit        |
|----------------------------|-------|-------------|
| startPos / endPos          | raw   | mm          |
| driveStrokeRevolution10    | ÷ 10  | revolutions |
| recoveryStrokeRevolution10 | ÷ 10  | revolutions |
| averageWatts10             | ÷ 10  | watts       |

Also: `Ds2` (V2 variant, same format)

#### Other response prefixes

| Prefix | Meaning               |
|--------|-----------------------|
| `Rl`   | Resistance level      |
| `Rv`   | Firmware version      |
| `Rs`   | Serial number         |
| `Rh`   | Health status         |
| `Sr`   | Reboot complete       |
| `!!`   | Error                 |
| `e0`   | Error response        |
| `Re`   | Error conditions      |

### Resistance safe range

```
50 ≤ level ≤ 200
```

Never send values outside this range.

---

## Permission Notes

`/dev/ttyS1` is `crw-rw---- system system`. Our sideloaded app needs system UID.

Both `com.truerowing.crew` and `com.truerowing.hydrowlauncher` run as `system` UID and have no
exported content providers or services that relay serial data. Logcat from these processes
shows only network/connectivity events — no rowing telemetry logged at the default level.

**Options for gaining serial access (investigated 2026-03-13):**

| Approach | Status | Notes |
|---|---|---|
| `adb shell chmod 666 /dev/ttyS1` | **Blocked** | ADB shell is uid=2000, not root |
| `android:sharedUserId="android.uid.system"` | **Blocked** | Requires platform signing key; can't extract without root |
| Push APK to `/system/priv-app/` | **Blocked** | System partition read-only, no root |
| `adb root` | **Blocked** | Production build (`user/release-keys`) |
| `su` binary | **Absent** | Not present on device |
| Logcat sniffing from crew app | **No data** | Telemetry not logged at default level |
| IPC from crew app | **No data** | No exported services or content providers |
| **MTK-SU exploit** | **Untried** | Known to work on some MT8167/Android 10 builds |
| Fastboot + Magisk | **IN PROGRESS** | OEM bootloader unlocked via Developer Options (2026-03-14) |

Build fingerprint: `alps/foenix_h/foenix_h:10/QP1A.190711.020/1725505377:user/release-keys`

---

## Installed Packages of Interest

| Package                          | Location                 | Notes                    |
|----------------------------------|--------------------------|--------------------------|
| `com.truerowing.crew`            | `/data/app/...`          | Main app, runs as system |
| `com.truerowing.hydrowlauncher`  | `/system/priv-app/...`   | Stock launcher           |
| `com.dsi.ant.*`                  | system                   | ANT+ — heart rate only   |
| `com.mediatek.engineermode`      | system                   | Engineering menu present |

---

## Audio Signal Analysis

Although the stock app uses UART, the 3.5mm cable also carries an **analog sensor signal** readable via the tablet's audio input (no root required).

### Signal characteristics

| Property          | Value                                      |
|-------------------|--------------------------------------------|
| Type              | Clean sinusoid (NOT FSK-encoded serial)    |
| Frequency range   | ~100–400 Hz during active rowing (observed)|
| At rest           | RMS < ~170 (noise floor)                   |
| Active threshold  | RMS > ~500                                 |
| Active RMS range  | ~500–9000 (mean ~3244 in a 60s session)    |
| Sample rate used  | 44100 Hz, 16-bit mono                      |

### Waveform quality (confirmed 2026-03-13)

The signal is a **clean sinusoid**. FFT analysis during peak drive shows all spectral energy
concentrated at the fundamental — top 5 peaks have ratios 0.83–1.17× the fundamental, no
integer harmonics. Zero-crossing frequency (267 Hz) matches FFT peak (240–260 Hz) closely.
Autocorrelation is reliable; harmonic ambiguity previously noted appears to have been resolved
by the boundary rejection threshold (`bestCorr < 0.3`).

Stroke pattern is clearly visible: sawtooth frequency envelope, rising during drive (~20–30 windows),
falling during recovery. Valley depth ~100–150 Hz below peak. At ~20 SPM cadence the pattern
is unambiguous.

### Frequency → RPM

Signal frequency tracks flywheel rotation speed. Relationship:

```
rps = freqHz / PULSES_PER_REV
rpm = rps * 60
watts = POWER_K * rps³
```

Current calibration constants:
- `PULSES_PER_REV = 60` — default; **48 is the next candidate to try** (see below)
- `POWER_K = 4.0` — uncalibrated

### PULSES_PER_REV calibration analysis (2026-03-13)

From a 60-second rowing session (`signal_1773438798773.pcm`):
- Peak drive frequency: ~240–267 Hz
- Recovery valley frequency: ~140 Hz

Plausible candidates (typical flywheel: 80–250 RPM idle, 200–500 RPM peak drive):

| Pulses/rev | RPM at valley (140 Hz) | RPM at peak (267 Hz) | Assessment |
|---|---|---|---|
| 36 | 233 | 400 | Peak may be high |
| **48** | **175** | **300** | **Most plausible** |
| 60 | 140 | 240 | Peak feels low for hard effort |
| 72 | 117 | 200 | Too slow |

**Recommended next value: `PULSES_PER_REV = 48`**

To validate definitively: need serial port access (UART gives actual RPM directly) or
physical inspection of flywheel sensor pole count.

### Permission status

```
/dev/ttyS1  crw-rw----  system system
```

`chmod 666` via `adb shell` fails (shell user, not root). UART path blocked without system signing or root.
See Permission Notes section for full investigation summary.

---

## Experiment Log

### 2026-03-12

**TEST:** ADB connection and device enumeration
**RESULT:** Connected via Wi-Fi (10.0.1.18), later ethernet (10.0.1.20). Pulled both APKs, decompiled with jadx.

**TEST:** Reverse-engineered `com.truerowing.crew` APK
**RESULT:** Found `CrewSerialManager.kt` — full UART serial protocol recovered. 3.5mm audio assumption was initially incorrect — but audio input DOES carry usable analog signal.

**TEST:** Sideload with `android:sharedUserId="android.uid.system"`
**RESULT:** `INSTALL_FAILED_SHARED_USER_INCOMPATIBLE` — requires platform signing key. System partition is read-only, `chmod` on ttyS1 denied. UART path blocked.

**TEST:** Audio capture via `AudioRecord` (RECORD_AUDIO permission only)
**RESULT:** Clear sinusoidal signal received. Frequency tracks flywheel speed. Noise floor ~170 RMS, active signal up to ~8000 RMS. Signal present on both L and R channels (standard TRS, not TRRS).

**TEST:** Autocorrelation pitch detection (100ms windows, 50–600 Hz range)
**RESULT:** Stable frequency tracking. Some harmonic ambiguity (2× flipping) mitigated with EMA smoothing. RPM display feels accurate at ~1–2 RPS during steady rowing.

**NEXT:** Calibrate `PULSES_PER_REV` with controlled spin test. Implement proper revolution counter and stroke detection from frequency envelope.

### 2026-03-14

**OBSERVATION:** Physical inspection of tablet rear I/O panel (see `docs/IMG_0723.jpeg`).
**RESULT:** Confirmed ports: 3.5mm jack (UART/sensor cable), barrel power, RJ45 ethernet, micro-USB. Two cables currently plugged in: 3.5mm TRS (to rowing machine control board) and barrel power.

**ACTION:** OEM bootloader unlocked via Developer Options.
**RESULT:** Fastboot + Magisk path is now viable. Device booted into fastboot mode successfully.
**NOTE:** Fastboot only works over USB — ethernet is unavailable in fastboot mode. Must use micro-USB cable connected to a laptop to proceed.

**NEXT:** Connect via USB, confirm with `fastboot devices` + `fastboot getvar unlocked`, then flash Magisk-patched boot image to gain root. Root will allow `chmod 666 /dev/ttyS1` (or persistent init.d equivalent), unblocking direct UART access and `PULSES_PER_REV` calibration.
