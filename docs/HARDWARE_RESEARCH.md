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

## Experiment Log

### 2026-03-12

**TEST:** ADB connection and device enumeration
**RESULT:** Connected via Wi-Fi (10.0.1.18), later ethernet (10.0.1.20). Pulled both APKs, decompiled with jadx.

**TEST:** Reverse-engineered `com.truerowing.crew` APK
**RESULT:** Found `CrewSerialManager.kt` — full UART serial protocol recovered. 3.5mm audio assumption was incorrect.

**NEXT:** Build hydropen app, attempt `chmod 666 /dev/ttyS1` for dev access, then connect and stream live telemetry.
