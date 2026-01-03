import pickle
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from PySide6.QtCore import QObject

from src.utils.audio_utils import AudioUtils
from src.utils.ffmpeg_wrapper import FFmpegWrapper


class SpectrogramData(QObject):
    """Computes and caches spectrogram data from audio files

    Uses STFT (Short-Time Fourier Transform) to convert audio into
    frequency-domain representation for visualization.
    """

    def __init__(self, file_path: Path, parent: Optional[QObject] = None):
        """Initialize spectrogram data

        Args:
            file_path: Path to audio file
            parent: Parent QObject
        """
        super().__init__(parent)

        self._file_path = file_path
        self._spectrogram: Optional[np.ndarray] = None
        self._frequency_bins: Optional[np.ndarray] = None

        # Cache file path (same directory as audio, with .spec extension)
        self._cache_file = file_path.with_suffix(file_path.suffix + ".spec")

    def extract_spectrogram(
        self,
        n_fft: int = 2048,
        hop_length: int = 512,
        freq_min: float = 80.0,
        freq_max: float = 8000.0,
        use_cache: bool = True,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute or load cached spectrogram

        Args:
            n_fft: FFT window size
            hop_length: Hop size between frames
            freq_min: Minimum frequency to include (Hz)
            freq_max: Maximum frequency to include (Hz)
            use_cache: Whether to use cached data if available

        Returns:
            Tuple of (spectrogram, frequency_bins)
            - spectrogram: 2D array [time_bins, freq_bins] with dB values
            - frequency_bins: 1D array of frequency values in Hz
        """
        # Try to load from cache first
        if use_cache and self._load_from_cache():
            return self._spectrogram, self._frequency_bins

        # Extract audio data from file using FFmpeg
        ffmpeg = FFmpegWrapper()

        # Get raw audio data - use higher resolution for spectrogram
        # Extract as 48kHz mono for good frequency resolution
        audio_data = ffmpeg.extract_audio_samples(
            self._file_path, sample_rate=48000, channels=1
        )

        if audio_data is None or len(audio_data) == 0:
            # Return empty spectrogram if extraction failed
            return np.array([[]]), np.array([])

        # Compute STFT
        spectrogram, frequencies = AudioUtils.compute_stft(
            audio_data,
            sample_rate=48000,
            n_fft=n_fft,
            hop_length=hop_length,
            window="hann",
        )

        # Filter to voice frequency range
        spectrogram, frequencies = AudioUtils.filter_frequency_range(
            spectrogram, frequencies, freq_min, freq_max
        )

        # Store results
        self._spectrogram = spectrogram
        self._frequency_bins = frequencies

        # Cache for future use
        self._save_to_cache()

        return self._spectrogram, self._frequency_bins

    def _save_to_cache(self) -> None:
        """Save computed spectrogram to cache file"""
        if self._spectrogram is None or self._frequency_bins is None:
            return

        try:
            cache_data = {
                "spectrogram": self._spectrogram,
                "frequency_bins": self._frequency_bins,
                "file_mtime": self._file_path.stat().st_mtime,  # For cache validation
            }

            with open(self._cache_file, "wb") as f:
                pickle.dump(cache_data, f)

        except Exception as e:
            # Cache save failure is non-fatal
            print(f"Warning: Failed to save spectrogram cache: {e}")

    def _load_from_cache(self) -> bool:
        """Load spectrogram from cache if valid

        Returns:
            True if cache was loaded successfully
        """
        if not self._cache_file.exists():
            return False

        try:
            # Check if cache is newer than source file
            cache_mtime = self._cache_file.stat().st_mtime
            file_mtime = self._file_path.stat().st_mtime

            if cache_mtime < file_mtime:
                # Cache is outdated
                return False

            # Load cache
            with open(self._cache_file, "rb") as f:
                cache_data = pickle.load(f)

            # Validate cache
            if cache_data.get("file_mtime") != file_mtime:
                return False

            self._spectrogram = cache_data["spectrogram"]
            self._frequency_bins = cache_data["frequency_bins"]

            return True

        except Exception as e:
            # Cache load failure - will recompute
            print(f"Warning: Failed to load spectrogram cache: {e}")
            return False

    def get_spectrogram(self) -> Optional[np.ndarray]:
        """Get cached spectrogram data

        Returns:
            Spectrogram array or None if not computed
        """
        return self._spectrogram

    def get_frequency_bins(self) -> Optional[np.ndarray]:
        """Get cached frequency bins

        Returns:
            Frequency bins array or None if not computed
        """
        return self._frequency_bins
