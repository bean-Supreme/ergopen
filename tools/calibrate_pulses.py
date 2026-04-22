#!/usr/bin/env python3
"""
Calibrate PULSES_PER_REV by inspecting raw signal cycles and power spectrum.
Usage: python3 calibrate_pulses.py <file.pcm>
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

SAMPLE_RATE = 44100

def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "signal_captures/signal_1773438798773.pcm")
    samples = np.frombuffer(path.read_bytes(), dtype="<i2").astype(np.float32)
    duration = len(samples) / SAMPLE_RATE
    print(f"Loaded {duration:.1f}s from {path.name}")

    fig = plt.figure(figsize=(16, 12))
    fig.suptitle("Pulse calibration — " + path.name, fontsize=11)

    # ── 1. Raw waveform: 50ms window at peak drive (~25s in) ──────────────────
    # Pick a moment near the middle of the session during a drive (high RMS)
    window_ms = 50
    window_n = int(SAMPLE_RATE * window_ms / 1000)

    # Find the 1s chunk with highest RMS (peak drive)
    chunk = int(SAMPLE_RATE)
    rms_chunks = [np.sqrt(np.mean(samples[i:i+chunk]**2)) for i in range(0, len(samples)-chunk, chunk)]
    best_sec = int(np.argmax(rms_chunks))
    # Within that second, pick the 50ms with highest RMS
    start_s = best_sec * SAMPLE_RATE
    rms_wins = [np.sqrt(np.mean(samples[start_s+i:start_s+i+window_n]**2))
                for i in range(0, chunk - window_n, window_n)]
    best_win = int(np.argmax(rms_wins))
    start = start_s + best_win * window_n
    raw_win = samples[start:start + window_n]
    t_ms = np.arange(window_n) / SAMPLE_RATE * 1000

    ax1 = fig.add_subplot(3, 2, (1, 2))
    ax1.plot(t_ms, raw_win, color="steelblue", linewidth=0.7)
    ax1.set_title(f"Raw waveform — 50ms window at t={best_sec:.1f}s (peak drive)")
    ax1.set_xlabel("Time (ms)")
    ax1.set_ylabel("Amplitude")

    # Count zero-crossings (upward) to estimate frequency
    zc = np.where((raw_win[:-1] < 0) & (raw_win[1:] >= 0))[0]
    if len(zc) >= 2:
        avg_period_samples = np.diff(zc).mean()
        measured_hz = SAMPLE_RATE / avg_period_samples
        print(f"Zero-crossing freq at peak drive: {measured_hz:.1f} Hz  ({len(zc)} upward crossings in {window_ms}ms)")
        ax1.axvline(zc[0] / SAMPLE_RATE * 1000, color='red', alpha=0.3, linewidth=0.5)
        for z in zc:
            ax1.axvline(z / SAMPLE_RATE * 1000, color='red', alpha=0.2, linewidth=0.5)
        ax1.set_title(f"Raw waveform — 50ms @ t={best_sec:.1f}s | zero-crossing freq: {measured_hz:.1f} Hz")

    # ── 2. Power spectrum of same window ──────────────────────────────────────
    ax2 = fig.add_subplot(3, 2, 3)
    spectrum = np.abs(np.fft.rfft(raw_win * np.hanning(window_n))) ** 2
    freqs = np.fft.rfftfreq(window_n, 1 / SAMPLE_RATE)
    mask = (freqs >= 30) & (freqs <= 1000)
    ax2.plot(freqs[mask], spectrum[mask], color="orange", linewidth=0.8)
    ax2.set_title("Power spectrum (peak drive window)")
    ax2.set_xlabel("Frequency (Hz)")
    ax2.set_ylabel("Power")
    # Mark top 5 peaks
    peak_idx = np.argsort(spectrum[mask])[-5:][::-1]
    for pi in peak_idx:
        f = freqs[mask][pi]
        ax2.axvline(f, color='red', linestyle='--', alpha=0.6, linewidth=0.8)
        ax2.text(f + 2, spectrum[mask][pi] * 0.9, f"{f:.0f}", fontsize=7, color='red')
    fund = freqs[mask][np.argmax(spectrum[mask])]
    print(f"Dominant spectral peak at peak drive: {fund:.1f} Hz")
    # Check for harmonics
    harmonic_ratios = [freqs[mask][pi] / fund for pi in peak_idx]
    print(f"Top 5 spectral peaks: {[f'{freqs[mask][pi]:.0f}Hz' for pi in peak_idx]}")
    print(f"Ratios to fundamental: {[f'{r:.2f}' for r in harmonic_ratios]}")

    # ── 3. Power spectrum at recovery valley ──────────────────────────────────
    # Find lowest-RMS active window (valley)
    rms_wins_all = [np.sqrt(np.mean(samples[i:i+window_n]**2)) for i in range(0, len(samples)-window_n, window_n)]
    rms_arr = np.array(rms_wins_all)
    active_mask = rms_arr > 500
    if active_mask.any():
        valley_idx = int(np.where(active_mask, rms_arr, np.inf).argmin())
        start_v = valley_idx * window_n
        valley_win = samples[start_v:start_v + window_n]
        t_valley = start_v / SAMPLE_RATE

        ax3 = fig.add_subplot(3, 2, 4)
        spectrum_v = np.abs(np.fft.rfft(valley_win * np.hanning(window_n))) ** 2
        ax3.plot(freqs[mask], spectrum_v[mask], color="green", linewidth=0.8)
        fund_v = freqs[mask][np.argmax(spectrum_v[mask])]
        ax3.axvline(fund_v, color='red', linestyle='--', alpha=0.6, linewidth=0.8)
        ax3.set_title(f"Power spectrum (recovery valley @ t={t_valley:.1f}s) — peak: {fund_v:.0f} Hz")
        ax3.set_xlabel("Frequency (Hz)")
        ax3.set_ylabel("Power")
        print(f"Dominant spectral peak at recovery valley: {fund_v:.1f} Hz")

    # ── 4. Pulses/rev table ───────────────────────────────────────────────────
    ax4 = fig.add_subplot(3, 2, (5, 6))
    ax4.axis('off')
    candidates = [1, 2, 3, 4, 6, 8, 12, 16, 24, 30, 36, 48, 60, 72]
    rows = [["Pulses/rev", "RPM at valley", "RPM at peak", "Notes"]]
    for p in candidates:
        rpm_valley = (fund_v / p) * 60 if active_mask.any() else 0
        rpm_peak = (fund / p) * 60
        note = ""
        if 80 <= rpm_valley <= 250 and 200 <= rpm_peak <= 700:
            note = "← plausible"
        rows.append([str(p), f"{rpm_valley:.0f}", f"{rpm_peak:.0f}", note])
    tbl = ax4.table(cellText=rows[1:], colLabels=rows[0], loc='center', cellLoc='center')
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1, 1.4)
    # Highlight plausible rows
    for i, row in enumerate(rows[1:]):
        if "plausible" in row[3]:
            for j in range(4):
                tbl[i+1, j].set_facecolor("#d4f4d4")
    ax4.set_title("RPM estimates by pulses/rev (typical flywheel: 80–250 RPM at rest → 200–600 RPM at peak)")

    plt.tight_layout()
    out = path.with_suffix(".calibration.png")
    plt.savefig(out, dpi=150)
    print(f"\nSaved to {out}")

if __name__ == "__main__":
    main()
