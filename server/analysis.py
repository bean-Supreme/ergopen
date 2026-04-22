"""
Signal analysis pipeline.

Pure functions plus StrokeDetector (stateful, lives in app state).
"""

import time
import numpy as np

SAMPLE_RATE     = 44100
FFT_SIZE        = 4096
MIN_HZ          = 50
MAX_HZ          = 600
NOISE_FLOOR     = 170
ACTIVE_THRESH   = 500
POWER_K         = 4.0      # uncalibrated: watts = K * rps³
WAVEFORM_POINTS = 512

_freqs    = np.fft.rfftfreq(FFT_SIZE, 1 / SAMPLE_RATE)
_fft_mask = (_freqs >= MIN_HZ) & (_freqs <= MAX_HZ)
FFT_FREQS: list[float] = _freqs[_fft_mask].tolist()


# ── Pure signal functions ──────────────────────────────────────────────────────

def pitch_autocorr(samples: np.ndarray) -> float | None:
    x = np.asarray(samples, dtype=np.float64)
    x -= x.mean()
    rms = np.sqrt(np.mean(x ** 2))
    if rms < NOISE_FLOOR:
        return None
    x /= rms

    min_lag = int(SAMPLE_RATE / MAX_HZ)
    max_lag = min(int(SAMPLE_RATE / MIN_HZ), len(x) - 1)

    n   = len(x)
    fft = np.fft.rfft(x, n=2 * n)
    acf = np.fft.irfft(fft * np.conj(fft))[:n]
    if acf[0] == 0:
        return None
    acf /= acf[0]

    best_lag  = np.argmax(acf[min_lag:max_lag]) + min_lag
    if acf[best_lag] < 0.3:
        return None
    return float(SAMPLE_RATE / best_lag)


def compute_fft(samples: np.ndarray) -> list[float]:
    if len(samples) < FFT_SIZE:
        return [0.0] * len(FFT_FREQS)
    chunk  = samples[-FFT_SIZE:]
    window = np.hanning(FFT_SIZE)
    mag    = np.abs(np.fft.rfft(chunk * window))
    return mag[_fft_mask].tolist()


def downsample_waveform(samples: np.ndarray) -> list[float]:
    display_len = SAMPLE_RATE // 10
    chunk = samples[-display_len:] if len(samples) >= display_len else samples
    if len(chunk) == 0:
        return [0.0] * WAVEFORM_POINTS
    idx         = np.linspace(0, len(chunk) - 1, WAVEFORM_POINTS, dtype=int)
    downsampled = chunk[idx] / 32768.0
    return downsampled.tolist()


def split_from_watts(watts: float) -> float | None:
    """Seconds per 500m using the standard ergometer formula: P = 2.8 / (t/500)³"""
    if watts <= 0:
        return None
    return 500.0 * (2.8 / watts) ** (1.0 / 3.0)


# ── Stroke detector ────────────────────────────────────────────────────────────

class StrokeDetector:
    """
    Detects rowing strokes from the EMA-smoothed frequency signal.

    A stroke is counted when the frequency transitions from falling (recovery)
    to rising (drive) while still near the valley — i.e. drive-start.

    SPM is derived from the mean inter-stroke interval over the last 8 strokes,
    clamped to the last 60 seconds.
    """

    _EMA_ALPHA      = 0.08   # aggressive smoothing for stroke shape
    _PEAK_DECAY     = 0.998  # how quickly the recent-peak estimate decays
    _VALLEY_RATIO   = 0.78   # drive starts below this fraction of recent peak
    _MIN_STROKE_SEC = 1.2    # minimum time between strokes (~50 SPM max)
    _MAX_HISTORY    = 60.0   # seconds of stroke history to keep

    def __init__(self) -> None:
        self._ema:          float | None = None
        self._prev_ema:     float | None = None
        self._recent_peak:  float        = 0.0
        self._in_recovery:  bool         = False
        self._stroke_times: list[float]  = []

    def update(self, freq: float | None) -> float | None:
        """
        Feed the latest EMA-smoothed frequency. Returns current SPM or None.
        Call once per broadcast frame.
        """
        if freq is None:
            self._ema = None
            self._prev_ema = None
            return None

        alpha     = self._EMA_ALPHA
        self._ema = freq if self._ema is None else alpha * freq + (1 - alpha) * self._ema
        ema       = self._ema

        self._recent_peak = max(self._recent_peak * self._PEAK_DECAY, ema)

        if self._prev_ema is not None:
            rising           = ema > self._prev_ema
            valley_threshold = self._recent_peak * self._VALLEY_RATIO

            if not rising:
                self._in_recovery = True

            if self._in_recovery and rising and ema < valley_threshold:
                now = time.monotonic()
                if (not self._stroke_times or
                        now - self._stroke_times[-1] >= self._MIN_STROKE_SEC):
                    self._stroke_times.append(now)
                    self._in_recovery = False

        self._prev_ema = ema

        # Prune old strokes
        cutoff = time.monotonic() - self._MAX_HISTORY
        self._stroke_times = [t for t in self._stroke_times if t >= cutoff]

        return self._spm()

    def _spm(self) -> float | None:
        n = len(self._stroke_times)
        if n < 2:
            return None
        recent    = self._stroke_times[-min(n, 8):]
        intervals = [recent[i + 1] - recent[i] for i in range(len(recent) - 1)]
        return 60.0 / (sum(intervals) / len(intervals))

    def reset(self) -> None:
        self._ema          = None
        self._prev_ema     = None
        self._recent_peak  = 0.0
        self._in_recovery  = False
        self._stroke_times = []


# ── Main analysis entry point ──────────────────────────────────────────────────

def analyze(samples: np.ndarray, ppr: int, ema_freq: float | None) -> dict:
    rms      = float(np.sqrt(np.mean(samples[-2048:] ** 2))) if len(samples) >= 2048 else 0.0
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
        'ema_freq':  ema_freq,
    }
