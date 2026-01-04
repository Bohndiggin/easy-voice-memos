import pickle
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from PySide6.QtCore import QObject, QThread, Signal

from src.utils.audio_utils import AudioUtils
from src.utils.ffmpeg_wrapper import FFmpegWrapper


class SpectrogramWorker(QThread):
    """Background thread for spectrogram computation"""

    # Signals
    progress_updated = Signal(str)  # Progress message
    computation_finished = Signal(object, object)  # (spectrogram, freq_bins)
    computation_failed = Signal(str)  # Error message

    def __init__(
        self,
        file_path: Path,
        n_fft: int = 1024,
        hop_length: int = 1024,
        freq_min: float = 80.0,
        freq_max: float = 8000.0,
        parent: Optional[QObject] = None
    ):
        """Initialize spectrogram worker

        Args:
            file_path: Path to audio file
            n_fft: FFT window size
            hop_length: Hop size between frames
            freq_min: Minimum frequency (Hz)
            freq_max: Maximum frequency (Hz)
            parent: Parent QObject
        """
        super().__init__(parent)
        self._file_path = file_path
        self._n_fft = n_fft
        self._hop_length = hop_length
        self._freq_min = freq_min
        self._freq_max = freq_max
        self._cancelled = False

    def run(self) -> None:
        """Execute spectrogram computation in background thread"""
        try:
            # Try cache first (with parameter validation)
            self.progress_updated.emit("Loading cached spectrogram...")
            spec_data = SpectrogramData(self._file_path)

            if spec_data._load_from_cache(
                n_fft=self._n_fft,
                hop_length=self._hop_length,
                freq_min=self._freq_min,
                freq_max=self._freq_max
            ):
                self.computation_finished.emit(
                    spec_data._spectrogram,
                    spec_data._frequency_bins
                )
                return

            # Compute from scratch
            if self._cancelled:
                return

            self.progress_updated.emit("Extracting audio data...")

            ffmpeg = FFmpegWrapper()
            audio_info = ffmpeg.get_audio_info(self._file_path)
            file_sample_rate = audio_info.get("sample_rate", 48000)
            target_sample_rate = min(file_sample_rate, 16000)

            if self._cancelled:
                return

            audio_data = ffmpeg.extract_audio_samples(
                self._file_path,
                sample_rate=target_sample_rate,
                channels=1
            )

            if self._cancelled or audio_data is None or len(audio_data) == 0:
                self.computation_failed.emit("Failed to extract audio")
                return

            self.progress_updated.emit("Computing spectrogram...")

            # Compute STFT with medium quality settings
            spectrogram, frequencies = AudioUtils.compute_stft(
                audio_data,
                sample_rate=target_sample_rate,
                n_fft=self._n_fft,
                hop_length=self._hop_length,
                window="hann",
            )

            if self._cancelled:
                return

            # Filter to voice frequency range
            spectrogram, frequencies = AudioUtils.filter_frequency_range(
                spectrogram, frequencies, self._freq_min, self._freq_max
            )

            # Save to cache for next time
            spec_data._spectrogram = spectrogram
            spec_data._frequency_bins = frequencies
            spec_data._save_to_cache(
                n_fft=self._n_fft,
                hop_length=self._hop_length,
                freq_min=self._freq_min,
                freq_max=self._freq_max
            )

            # Emit results
            self.computation_finished.emit(spectrogram, frequencies)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.computation_failed.emit(str(e))

    def cancel(self) -> None:
        """Cancel the computation"""
        self._cancelled = True


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
        n_fft: int = 1024,
        hop_length: int = 1024,
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
        # Try to load from cache first with parameter validation
        if use_cache and self._load_from_cache(n_fft, hop_length, freq_min, freq_max):
            return self._spectrogram, self._frequency_bins

        # Extract audio data from file using FFmpeg
        ffmpeg = FFmpegWrapper()

        # Get file's actual sample rate
        audio_info = ffmpeg.get_audio_info(self._file_path)
        file_sample_rate = audio_info.get("sample_rate", 48000)

        # Use file's sample rate or downsample to 16kHz for efficiency if higher
        target_sample_rate = min(file_sample_rate, 16000)

        # Get raw audio data
        audio_data = ffmpeg.extract_audio_samples(
            self._file_path, sample_rate=target_sample_rate, channels=1
        )

        if audio_data is None or len(audio_data) == 0:
            # Return empty spectrogram if extraction failed
            return np.array([[]]), np.array([])

        # Compute STFT using the actual sample rate
        spectrogram, frequencies = AudioUtils.compute_stft(
            audio_data,
            sample_rate=target_sample_rate,
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

        # Cache for future use with parameters
        self._save_to_cache(n_fft, hop_length, freq_min, freq_max)

        return self._spectrogram, self._frequency_bins

    def _save_to_cache(
        self,
        n_fft: int = 1024,
        hop_length: int = 1024,
        freq_min: float = 80.0,
        freq_max: float = 8000.0
    ) -> None:
        """Save computed spectrogram to cache file with parameters

        Args:
            n_fft: FFT window size used
            hop_length: Hop size used
            freq_min: Minimum frequency used
            freq_max: Maximum frequency used
        """
        if self._spectrogram is None or self._frequency_bins is None:
            return

        try:
            cache_data = {
                "spectrogram": self._spectrogram,
                "frequency_bins": self._frequency_bins,
                "file_mtime": self._file_path.stat().st_mtime,
                "n_fft": n_fft,
                "hop_length": hop_length,
                "freq_min": freq_min,
                "freq_max": freq_max,
            }

            with open(self._cache_file, "wb") as f:
                pickle.dump(cache_data, f)

        except Exception as e:
            # Cache save failure is non-fatal
            print(f"Warning: Failed to save spectrogram cache: {e}")

    def _load_from_cache(
        self,
        n_fft: int = 1024,
        hop_length: int = 1024,
        freq_min: float = 80.0,
        freq_max: float = 8000.0
    ) -> bool:
        """Load spectrogram from cache if valid and parameters match

        Args:
            n_fft: Required FFT window size
            hop_length: Required hop size
            freq_min: Required minimum frequency
            freq_max: Required maximum frequency

        Returns:
            True if cache was loaded successfully with matching parameters
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

            # Validate file mtime
            if cache_data.get("file_mtime") != file_mtime:
                return False

            # Validate computation parameters match
            if (cache_data.get("n_fft") != n_fft or
                cache_data.get("hop_length") != hop_length or
                cache_data.get("freq_min") != freq_min or
                cache_data.get("freq_max") != freq_max):
                # Parameters don't match - need to recompute
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
