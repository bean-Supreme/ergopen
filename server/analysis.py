"""
Signal analysis pipeline.

All functions are pure (no side effects) so they can be called from the
async broadcast loop without locks.
"""

import numpy as np

SAMPLE_RATE     = 44100
FFT_SIZE        = 4096
MIN_HZ          = 50
MAX_HZ          = 600
NOISE_FLOOR     = 170      # RMS below this → treat as silence
ACTIVE_THRESH   = 500
POWER_K         = 4.0      # uncalibrated: watts = K * rps³
WAVEFORM_POINTS = 512      # downsampled display resolution

# Precompute FFT frequency mask (constant for fixed FFT_SIZE + SAMPLE_RATE)
_freqs    = np.fft.rfftfreq(FFT_SIZE, 1 / SAMPLE_RATE)
_fft_mask = (_freqs >= MIN_HZ) & (_freqs <= MAX_HZ)
FFT_FREQS: list[float] = _freqs[_fft_mask].tolist()   # sent to clients on init


def pitch_autocorr(samples: np.ndarray) -> float | None:
    """
    Autocorrelation-based pitch detection.
    Returns fundamental frequency in Hz, or None if below noise floor or
    correlation too weak.
    """
    x = np.asarray(samples, dtype=np.float64)
    x -= x.mean()
    rms = np.sqrt(np.mean(x ** 2))
    if rms < NOISE_FLOOR:
        return None

    x /= rms  # normalize before correlation

    min_lag = int(SAMPLE_RATE / MAX_HZ)
    max_lag = min(int(SAMPLE_RATE / MIN_HZ), len(x) - 1)

    n   = len(x)
    fft = np.fft.rfft(x, n=2 * n)
    acf = np.fft.irfft(fft * np.conj(fft))[:n]
    if acf[0] == 0:
        return None
    acf /= acf[0]

    best_lag  = np.argmax(acf[min_lag:max_lag]) + min_lag
    best_corr = acf[best_lag]
    if best_corr < 0.3:
        return None

    return float(SAMPLE_RATE / best_lag)


def compute_fft(samples: np.ndarray) -> list[float]:
    """Returns FFT magnitudes for the 50–600 Hz range (matches FFT_FREQS)."""
    if len(samples) < FFT_SIZE:
        return [0.0] * len(FFT_FREQS)

    chunk  = samples[-FFT_SIZE:]
    window = np.hanning(FFT_SIZE)
    mag    = np.abs(np.fft.rfft(chunk * window))
    return mag[_fft_mask].tolist()


def downsample_waveform(samples: np.ndarray) -> list[float]:
    """Last ~100ms of signal, downsampled to WAVEFORM_POINTS, normalized [-1, 1]."""
    display_len = SAMPLE_RATE // 10   # 0.1 s
    chunk = samples[-display_len:] if len(samples) >= display_len else samples

    if len(chunk) == 0:
        return [0.0] * WAVEFORM_POINTS

    idx         = np.linspace(0, len(chunk) - 1, WAVEFORM_POINTS, dtype=int)
    downsampled = chunk[idx] / 32768.0   # normalize 16-bit range to [-1, 1]
    return downsampled.tolist()


def analyze(samples: np.ndarray, ppr: int, ema_freq: float | None) -> dict:
    """
    Full pipeline: waveform, FFT, pitch, RPM, watts.

    Returns analysis dict plus updated ema_freq for the caller to persist.
    """
    rms = float(np.sqrt(np.mean(samples[-2048:] ** 2))) if len(samples) >= 2048 else 0.0

    raw_freq = pitch_autocorr(samples[-FFT_SIZE:]) if len(samples) >= FFT_SIZE else None

    if raw_freq is not None:
        alpha    = 0.15
        ema_freq = raw_freq if ema_freq is None else alpha * raw_freq + (1 - alpha) * ema_freq
    else:
        ema_freq = None

    rpm = watts = None
    if ema_freq is not None:
        rps   = ema_freq / ppr
        rpm   = rps * 60
        watts = POWER_K * rps ** 3

    return {
        'rms':       rms,
        'freq':      ema_freq,
        'rpm':       rpm,
        'watts':     watts,
        'waveform':  downsample_waveform(samples),
        'fft_freqs': FFT_FREQS,
        'fft_mag':   compute_fft(samples),
        'is_active': rms > ACTIVE_THRESH,
        'ema_freq':  ema_freq,   # caller stores this for next frame
    }
