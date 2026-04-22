from pydantic import BaseModel
from typing import Optional


class DeviceInfo(BaseModel):
    index: int
    name: str
    max_input_channels: int
    default_samplerate: float


class Config(BaseModel):
    device: Optional[int] = None   # None = system default
    ppr: int = 48
    sample_rate: int = 44100


class ConfigUpdate(BaseModel):
    device: Optional[int] = None
    ppr: Optional[int] = None


class RecordingInfo(BaseModel):
    filename: str
    duration_s: float
    size_bytes: int


class ReplayRequest(BaseModel):
    filename: str


class SignalFrame(BaseModel):
    """
    Broadcast to all WebSocket clients at ~20 fps.

    waveform  — 512 samples, normalized to [-1, 1], last ~100ms of signal
    fft_freqs — Hz values for fft_mag bins (50–600 Hz range, constant)
    fft_mag   — FFT magnitudes for the corresponding frequencies
    """
    ts: float
    rms: float
    freq: Optional[float]          # fundamental Hz (EMA-smoothed), null if silent
    rpm: Optional[float]
    watts: Optional[float]         # uncalibrated: K * rps³
    waveform: list[float]
    fft_freqs: list[float]
    fft_mag: list[float]
    is_active: bool                # RMS above noise floor
    is_recording: bool
    rec_duration: float            # seconds recorded so far
    spm: Optional[float]           # strokes per minute, null if insufficient data
    split_sec: Optional[float]     # seconds per 500m, null if no power signal
