#!/usr/bin/env python3
"""
Inspect a raw PCM signal capture from the rowing machine.
Usage: python3 inspect_signal.py <file.pcm>
44100 Hz, 16-bit signed, little-endian mono
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

SAMPLE_RATE = 44100
WINDOW_MS = 100          # analysis window size
WINDOW = int(SAMPLE_RATE * WINDOW_MS / 1000)
MIN_FREQ = 50
MAX_FREQ = 600

def autocorr_freq(samples):
    min_lag = SAMPLE_RATE // MAX_FREQ
    max_lag = SAMPLE_RATE // MIN_FREQ
    energy = np.dot(samples, samples)
    if energy == 0:
        return 0.0
    n = len(samples)
    # FFT-based autocorrelation (fast)
    fft = np.fft.rfft(samples, n=2 * n)
    acf = np.fft.irfft(fft * np.conj(fft))[:n] / energy
    lags = slice(min_lag, min(max_lag, n - 1))
    best_lag = min_lag + int(np.argmax(acf[lags]))
    best_corr = acf[best_lag]
    if best_lag <= min_lag or best_corr < 0.3:
        return 0.0
    return SAMPLE_RATE / best_lag

def fft_freq(samples):
    n = len(samples)
    spectrum = np.abs(np.fft.rfft(samples * np.hanning(n)))
    freqs = np.fft.rfftfreq(n, 1 / SAMPLE_RATE)
    mask = (freqs >= MIN_FREQ) & (freqs <= MAX_FREQ)
    if not mask.any():
        return 0.0
    return freqs[mask][np.argmax(spectrum[mask])]

def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "signal_captures/signal_1773438798773.pcm")
    samples = np.frombuffer(path.read_bytes(), dtype="<i2").astype(np.float32)
    print(f"Loaded {len(samples)/SAMPLE_RATE:.1f}s ({len(samples)} samples) from {path.name}")

    n_windows = len(samples) // WINDOW
    times = np.arange(n_windows) * WINDOW_MS / 1000

    rms      = np.zeros(n_windows)
    freq_ac  = np.zeros(n_windows)
    freq_fft = np.zeros(n_windows)

    for i in range(n_windows):
        win = samples[i * WINDOW:(i + 1) * WINDOW]
        rms[i] = np.sqrt(np.mean(win ** 2))
        if rms[i] > 500:
            freq_ac[i]  = autocorr_freq(win)
            freq_fft[i] = fft_freq(win)

    # Smooth autocorr with EMA (alpha=0.3, matches AudioSensor)
    alpha = 0.3
    smoothed = np.zeros(n_windows)
    for i in range(n_windows):
        if freq_ac[i] > 0:
            smoothed[i] = alpha * freq_ac[i] + (1 - alpha) * smoothed[i - 1]
        elif rms[i] < 500:
            smoothed[i] = smoothed[i - 1] * 0.8
        else:
            smoothed[i] = smoothed[i - 1]

    print(f"RMS   — min: {rms.min():.0f}  max: {rms.max():.0f}  mean: {rms.mean():.0f}")
    active = freq_fft[freq_fft > 0]
    if len(active):
        print(f"Freq  — min: {active.min():.1f} Hz  max: {active.max():.1f} Hz  mean: {active.mean():.1f} Hz")

    fig, axes = plt.subplots(3, 1, figsize=(14, 9), sharex=True)
    fig.suptitle(path.name, fontsize=11)

    axes[0].plot(times, rms, color="steelblue", linewidth=0.8)
    axes[0].axhline(500, color="red", linestyle="--", linewidth=0.7, label="noise threshold")
    axes[0].set_ylabel("RMS amplitude")
    axes[0].legend(fontsize=8)

    axes[1].plot(times, freq_fft, color="orange", linewidth=0.8, label="FFT", alpha=0.7)
    axes[1].plot(times, freq_ac,  color="green",  linewidth=0.8, label="autocorr", alpha=0.7)
    axes[1].set_ylabel("Frequency (Hz)")
    axes[1].set_ylim(0, MAX_FREQ + 50)
    axes[1].legend(fontsize=8)

    axes[2].plot(times, smoothed, color="cyan", linewidth=1.0, label="smoothed (EMA)")
    axes[2].set_ylabel("Smoothed freq (Hz)")
    axes[2].set_xlabel("Time (s)")
    axes[2].set_ylim(0, MAX_FREQ + 50)
    axes[2].legend(fontsize=8)

    plt.tight_layout()
    out = path.with_suffix(".png")
    plt.savefig(out, dpi=150)
    print(f"Saved plot to {out}")
    plt.show()

if __name__ == "__main__":
    main()
