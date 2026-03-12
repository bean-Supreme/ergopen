# Hardware Research Log

---

## Device

| Item            | Value                        |
|-----------------|------------------------------|
| Model           | `foenix_h`                   |
| SoC             | MediaTek (`alps`)            |
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

Options (in order of preference for dev):
1. `adb shell chmod 666 /dev/ttyS1` — try first, costs nothing
2. `android:sharedUserId="android.uid.system"` + sign with AOSP platform test key
3. Push APK to `/system/priv-app/` via adb after remounting system partition

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
| Type              | Sinusoidal analog (NOT FSK-encoded serial) |
| Frequency range   | ~85–320 Hz during active rowing            |
| At rest           | RMS < ~170 (noise floor)                   |
| Active threshold  | RMS > ~500                                 |
| Sample rate used  | 44100 Hz, 16-bit mono                      |

### Frequency → RPM

Signal frequency tracks flywheel rotation speed. Relationship:

```
rps = freqHz / PULSES_PER_REV
rpm = rps * 60
watts = POWER_K * rps³
```

Current calibration constants (approximate, needs tuning):
- `PULSES_PER_REV = 60` — feels close (~1.9 RPS in steady rowing)
- `POWER_K = 4.0` — uncalibrated

### Waveform notes

- Non-sinusoidal: strong 2nd harmonic causes autocorrelation to sometimes lock on 2× the fundamental
- Spurious spikes occur when autocorrelation best-lag hits the search boundary
- Mitigated with: upper frequency limit of 600 Hz, boundary rejection, exponential smoothing (α=0.3)

### Permission status

```
/dev/ttyS1  crw-rw----  system system
```

`chmod 666` via `adb shell` fails (shell user, not root). UART path blocked without system signing or root.

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
