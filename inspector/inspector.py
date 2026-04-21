#!/usr/bin/env python3
"""
ergopen Signal Inspector — laptop edition

Captures the analog flywheel sensor signal from the 3.5mm audio jack and
displays real-time waveform, FFT spectrum, and RPM estimate.

Usage:
  python3 inspector.py                     # live capture (default device)
  python3 inspector.py <file.pcm>          # replay existing .pcm file
  python3 inspector.py --list              # list available audio devices
  python3 inspector.py --device N          # use device index N (from --list)
  python3 inspector.py --ppr N             # pulses-per-revolution (default: 48)

Keys during display:
  R  — start/stop recording (saves to ../signal_captures/)
  Q  — quit
"""

import argparse
import struct
import sys
import threading
import time
from collections import deque
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.gridspec import GridSpec

# ── Signal parameters ──────────────────────────────────────────────────────────
SAMPLE_RATE   = 44100
BLOCK_SIZE    = 1024
WAVEFORM_SECS = 0.10        # seconds of history shown in waveform plot
WAVEFORM_LEN  = int(SAMPLE_RATE * WAVEFORM_SECS)
FFT_SIZE      = 4096        # larger → finer frequency resolution (~10 Hz bins)
MIN_HZ        = 50
MAX_HZ        = 600
NOISE_FLOOR   = 170         # RMS below this is treated as silence
POWER_K       = 4.0         # uncalibrated: watts = K * rps³

# ── Shared state (ring buffer + recording) ─────────────────────────────────────
_ring   = deque(maxlen=SAMPLE_RATE * 4)   # 4 seconds of headroom
_lock   = threading.Lock()
_rec_buf: list[float] = []
_is_rec = False
_stop   = threading.Event()


# ── Audio callback ─────────────────────────────────────────────────────────────

def _audio_callback(indata, frames, time_info, status):
    """sounddevice callback — runs in audio thread."""
    global _is_rec
    samples = indata[:, 0].copy()
    with _lock:
        _ring.extend(samples)
    if _is_rec:
        _rec_buf.extend(samples)


# ── Signal analysis ────────────────────────────────────────────────────────────

def pitch_autocorr(samples: np.ndarray) -> float | None:
    """
    Autocorrelation pitch detection over the given sample window.
    Returns fundamental frequency in Hz, or None if signal is below noise floor
    or correlation is too weak.
    """
    x = np.asarray(samples, dtype=np.float64)
    x -= x.mean()
    rms = np.sqrt(np.mean(x ** 2))
    if rms < NOISE_FLOOR:
        return None

    x /= rms  # normalize before correlation

    min_lag = int(SAMPLE_RATE / MAX_HZ)
    max_lag = min(int(SAMPLE_RATE / MIN_HZ), len(x) - 1)

    # ACF via FFT (O(n log n) vs O(n²) direct)
    n = len(x)
    fft = np.fft.rfft(x, n=2 * n)
    acf = np.fft.irfft(fft * np.conj(fft))[:n]
    if acf[0] == 0:
        return None
    acf /= acf[0]

    best_lag = np.argmax(acf[min_lag:max_lag]) + min_lag
    if acf[best_lag] < 0.3:
        return None

    return SAMPLE_RATE / best_lag


def rpm_watts(freq_hz: float, ppr: int) -> tuple[float, float]:
    rps = freq_hz / ppr
    return rps * 60, POWER_K * rps ** 3


# ── Recording ──────────────────────────────────────────────────────────────────

def _save_recording(samples: list[float], out_path: Path) -> None:
    arr = np.array(samples)
    # Samples from sounddevice int16 are already in [-32768, 32767] range
    ints = np.clip(arr, -32768, 32767).astype(np.int16)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(struct.pack(f'<{len(ints)}h', *ints))
    print(f"Saved {len(ints)} samples ({len(ints)/SAMPLE_RATE:.1f}s) → {out_path}")


# ── Plot ───────────────────────────────────────────────────────────────────────

def _build_and_run_plot(stream, ppr: int, source: str) -> None:
    global _is_rec, _rec_buf

    BG      = '#1a1a2e'
    PANEL   = '#16213e'
    FG      = '#e0e0e0'
    DIM     = '#aaaacc'
    GRID    = '#2a2a4a'
    CYAN    = '#00d4ff'
    RED     = '#ff6b6b'
    GOLD    = '#ffd700'
    REC_RED = '#ff4444'

    fig = plt.figure(figsize=(13, 7))
    fig.patch.set_facecolor(BG)
    gs = GridSpec(3, 1, figure=fig, height_ratios=[2, 2, 1], hspace=0.45)

    ax_wave = fig.add_subplot(gs[0])
    ax_fft  = fig.add_subplot(gs[1])
    ax_stat = fig.add_subplot(gs[2])

    for ax in (ax_wave, ax_fft, ax_stat):
        ax.set_facecolor(PANEL)
        ax.tick_params(colors=FG, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(GRID)

    # Waveform subplot
    ax_wave.set_title('Waveform', color=FG, fontsize=10, pad=3)
    ax_wave.set_ylim(-35000, 35000)
    ax_wave.set_xlim(0, WAVEFORM_LEN)
    ax_wave.set_ylabel('amplitude', color=DIM, fontsize=8)
    ax_wave.axhline(0, color=GRID, linewidth=0.5)
    ax_wave.set_xticks([])
    (line_wave,) = ax_wave.plot(
        np.arange(WAVEFORM_LEN), np.zeros(WAVEFORM_LEN), color=CYAN, linewidth=0.8
    )

    # FFT subplot
    freqs    = np.fft.rfftfreq(FFT_SIZE, 1 / SAMPLE_RATE)
    fft_mask = (freqs >= MIN_HZ) & (freqs <= MAX_HZ)
    ax_fft.set_title('Frequency Spectrum', color=FG, fontsize=10, pad=3)
    ax_fft.set_xlim(MIN_HZ, MAX_HZ)
    ax_fft.set_ylim(0, 1)
    ax_fft.set_ylabel('magnitude', color=DIM, fontsize=8)
    ax_fft.set_xlabel('Hz', color=DIM, fontsize=8)
    (line_fft,) = ax_fft.plot(
        freqs[fft_mask], np.zeros(fft_mask.sum()), color=RED, linewidth=0.8
    )
    peak_vline = ax_fft.axvline(0, color=GOLD, linewidth=1.2, alpha=0.8)

    # Stats bar
    ax_stat.axis('off')
    stats_text = ax_stat.text(
        0.01, 0.5, '', transform=ax_stat.transAxes,
        color=FG, fontsize=11, verticalalignment='center', fontfamily='monospace',
    )
    rec_indicator = ax_stat.text(
        0.80, 0.5, '', transform=ax_stat.transAxes,
        color=REC_RED, fontsize=11, verticalalignment='center', fontfamily='monospace',
    )

    fig.suptitle(f'ergopen Signal Inspector  ·  {source}', color=FG, fontsize=12, y=0.98)

    ema_freq: float | None = None

    def update(_frame):
        nonlocal ema_freq

        with _lock:
            buf = np.array(_ring, dtype=np.float64)

        if len(buf) < FFT_SIZE:
            return line_wave, line_fft, peak_vline, stats_text, rec_indicator

        # ── Waveform ──
        wave = buf[-WAVEFORM_LEN:]
        wave = np.pad(wave, (max(0, WAVEFORM_LEN - len(wave)), 0))
        line_wave.set_ydata(wave)

        # ── FFT ──
        fft_chunk = buf[-FFT_SIZE:]
        window    = np.hanning(FFT_SIZE)
        mag       = np.abs(np.fft.rfft(fft_chunk * window))[fft_mask]
        line_fft.set_ydata(mag)
        if mag.max() > 0:
            ax_fft.set_ylim(0, mag.max() * 1.15)

        # ── Pitch detection (EMA smoothed) ──
        raw_freq = pitch_autocorr(fft_chunk)
        if raw_freq:
            alpha    = 0.15
            ema_freq = raw_freq if ema_freq is None else alpha * raw_freq + (1 - alpha) * ema_freq
            peak_vline.set_xdata([ema_freq])
            rpm, watts = rpm_watts(ema_freq, ppr)
            freq_str  = f'{ema_freq:6.1f} Hz'
            rpm_str   = f'{rpm:5.0f} RPM'
            watt_str  = f'{watts:6.1f} W'
        else:
            freq_str = rpm_str = watt_str = '  ----'

        rms = np.sqrt(np.mean(buf[-2048:] ** 2))
        stats_text.set_text(
            f'RMS {rms:6.0f}   '
            f'Freq {freq_str}   '
            f'RPM {rpm_str}   '
            f'Watts {watt_str} (uncal)   '
            f'PPR {ppr}'
        )

        rec_indicator.set_text(
            f'● REC  {len(_rec_buf) / SAMPLE_RATE:.1f}s' if _is_rec else ''
        )

        return line_wave, line_fft, peak_vline, stats_text, rec_indicator

    def on_key(event):
        global _is_rec, _rec_buf
        key = event.key.lower() if event.key else ''
        if key == 'q':
            _stop.set()
            plt.close('all')
        elif key == 'r':
            if not _is_rec:
                _rec_buf = []
                _is_rec  = True
                print('Recording started — press R again to save.')
            else:
                _is_rec = False
                ts  = int(time.time() * 1000)
                out = Path(__file__).parent.parent / 'signal_captures' / f'signal_{ts}.pcm'
                _save_recording(list(_rec_buf), out)

    fig.canvas.mpl_connect('key_press_event', on_key)

    if stream is not None:
        stream.start()

    _ani = animation.FuncAnimation(   # noqa: F841 — must be kept alive
        fig, update, interval=50, blit=True, cache_frame_data=False
    )

    try:
        plt.show()
    finally:
        _stop.set()
        if stream is not None:
            stream.stop()
            stream.close()


# ── Entry points ───────────────────────────────────────────────────────────────

def run_live(args) -> None:
    import sounddevice as sd

    device = args.device
    print(f'ergopen Signal Inspector')
    print(f'Device : {device if device is not None else "default (use --list to choose)"}')
    print(f'PPR    : {args.ppr}  |  SR: {SAMPLE_RATE} Hz')
    print(f'Keys   : R = record toggle, Q = quit')
    print()

    stream = sd.InputStream(
        device=device,
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='int16',
        blocksize=BLOCK_SIZE,
        callback=_audio_callback,
    )
    _build_and_run_plot(stream=stream, ppr=args.ppr, source='live')


def run_file(args) -> None:
    path = Path(args.file)
    if not path.exists():
        print(f'File not found: {path}', file=sys.stderr)
        sys.exit(1)

    raw     = path.read_bytes()
    samples = np.frombuffer(raw, dtype='<i2').astype(np.float64)
    print(f'Loaded {path.name}: {len(samples)} samples, {len(samples)/SAMPLE_RATE:.1f}s')

    def _feed():
        pos = 0
        while pos < len(samples) and not _stop.is_set():
            chunk = samples[pos : pos + BLOCK_SIZE]
            with _lock:
                _ring.extend(chunk)
            pos += BLOCK_SIZE
            time.sleep(BLOCK_SIZE / SAMPLE_RATE)

    threading.Thread(target=_feed, daemon=True).start()
    _build_and_run_plot(stream=None, ppr=args.ppr, source=path.name)


def main() -> None:
    parser = argparse.ArgumentParser(
        description='ergopen Signal Inspector',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('file',     nargs='?',          help='.pcm file to replay offline')
    parser.add_argument('--list',   action='store_true', help='List audio devices and exit')
    parser.add_argument('--device', type=int,            help='Audio device index (from --list)')
    parser.add_argument('--ppr',    type=int, default=48, help='Pulses per revolution (default: 48)')
    args = parser.parse_args()

    if args.list:
        import sounddevice as sd
        print(sd.query_devices())
        return

    if args.file:
        run_file(args)
    else:
        run_live(args)


if __name__ == '__main__':
    main()
