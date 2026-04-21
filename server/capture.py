"""
Audio capture — live and file-replay modes.

Both modes feed the same ring buffer so the analysis pipeline is identical
regardless of source.
"""

import struct
import threading
import time
from collections import deque
from pathlib import Path

import numpy as np

SAMPLE_RATE = 44100
BLOCK_SIZE  = 1024
RING_SECS   = 4


class AudioCapture:
    """Captures from a sounddevice input (3.5mm jack or any ALSA device)."""

    def __init__(self, device: int | None = None, sample_rate: int = SAMPLE_RATE):
        self.device      = device
        self.sample_rate = sample_rate

        self._ring: deque[float] = deque(maxlen=sample_rate * RING_SECS)
        self._lock = threading.Lock()

        self._rec_buf: list[float] = []
        self._is_recording = False

        self._stream = None
        self._replay_thread: threading.Thread | None = None
        self._replay_stop = threading.Event()

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start_live(self) -> None:
        """Start capturing from the audio device."""
        import sounddevice as sd

        self._stop_replay()
        if self._stream:
            return

        self._stream = sd.InputStream(
            device=self.device,
            samplerate=self.sample_rate,
            channels=1,
            dtype='int16',
            blocksize=BLOCK_SIZE,
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop_live(self) -> None:
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def start_replay(self, path: Path) -> None:
        """Feed a .pcm file into the ring buffer at real-time speed."""
        self.stop_live()
        self._stop_replay()

        raw     = path.read_bytes()
        samples = np.frombuffer(raw, dtype='<i2').astype(np.float64)

        self._replay_stop.clear()

        def _feed():
            pos = 0
            while pos < len(samples) and not self._replay_stop.is_set():
                chunk = samples[pos : pos + BLOCK_SIZE]
                with self._lock:
                    self._ring.extend(chunk)
                    if self._is_recording:
                        self._rec_buf.extend(chunk)
                pos += BLOCK_SIZE
                time.sleep(BLOCK_SIZE / self.sample_rate)

        self._replay_thread = threading.Thread(target=_feed, daemon=True)
        self._replay_thread.start()

    def shutdown(self) -> None:
        self.stop_live()
        self._stop_replay()

    def _stop_replay(self) -> None:
        if self._replay_thread and self._replay_thread.is_alive():
            self._replay_stop.set()
            self._replay_thread.join(timeout=2)
        self._replay_thread = None

    # ── Callback ───────────────────────────────────────────────────────────────

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        samples = indata[:, 0].copy().astype(np.float64)
        with self._lock:
            self._ring.extend(samples)
            if self._is_recording:
                self._rec_buf.extend(samples)

    # ── Samples ────────────────────────────────────────────────────────────────

    def get_samples(self) -> np.ndarray:
        with self._lock:
            return np.array(self._ring, dtype=np.float64)

    # ── Recording ──────────────────────────────────────────────────────────────

    def start_recording(self) -> None:
        self._rec_buf = []
        self._is_recording = True

    def stop_recording(self) -> list[float]:
        self._is_recording = False
        return list(self._rec_buf)

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def rec_duration(self) -> float:
        return len(self._rec_buf) / self.sample_rate
