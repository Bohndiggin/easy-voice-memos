from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from scipy import signal


class AudioUtils:
    """Helper functions for audio processing and formatting"""

    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in seconds to MM:SS or HH:MM:SS format

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration string (MM:SS or HH:MM:SS)
        """
        if seconds < 0:
            return "00:00"

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Format file size in bytes to human-readable format

        Args:
            size_bytes: File size in bytes

        Returns:
            Formatted file size (e.g., "2.5 MB", "128 KB")
        """
        if size_bytes < 0:
            return "0 B"

        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(size_bytes)
        unit_index = 0

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        if unit_index == 0:  # Bytes
            return f"{int(size)} {units[unit_index]}"
        return f"{size:.1f} {units[unit_index]}"

    @staticmethod
    def calculate_file_size(duration: float, bit_rate: Optional[int]) -> int:
        """Estimate file size based on duration and bit rate

        Args:
            duration: Duration in seconds
            bit_rate: Bit rate in bits per second (None for lossless)

        Returns:
            Estimated file size in bytes
        """
        if bit_rate is None:
            # Estimate for uncompressed WAV: sample_rate * bit_depth * channels / 8
            # Default assumption: 44.1kHz, 16-bit, stereo
            return int(duration * 44100 * 2 * 2)

        # For compressed formats: (bit_rate * duration) / 8
        return int((bit_rate * duration) / 8)

    @staticmethod
    def generate_filename(prefix: str = "memo", extension: str = ".wav") -> str:
        """Generate a unique filename with timestamp

        Args:
            prefix: Filename prefix (default: "memo")
            extension: File extension (default: ".wav")

        Returns:
            Filename in format: prefix_YYYYMMDD_HHMMSS.extension
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not extension.startswith("."):
            extension = f".{extension}"
        return f"{prefix}_{timestamp}{extension}"

    @staticmethod
    def validate_audio_file(file_path: Path) -> bool:
        """Check if file exists and has a valid audio extension

        Args:
            file_path: Path to audio file

        Returns:
            True if file exists and has valid audio extension
        """
        if not file_path.exists() or not file_path.is_file():
            return False

        valid_extensions = {
            ".wav",
            ".mp3",
            ".m4a",
            ".aac",
            ".opus",
            ".ogg",
            ".flac",
            ".wma",
            ".oga",
            ".spx",
        }

        return file_path.suffix.lower() in valid_extensions

    @staticmethod
    def parse_duration_string(duration_str: str) -> float:
        """Parse duration string (MM:SS or HH:MM:SS) to seconds

        Args:
            duration_str: Duration string

        Returns:
            Duration in seconds
        """
        try:
            parts = duration_str.split(":")
            if len(parts) == 2:  # MM:SS
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds
            elif len(parts) == 3:  # HH:MM:SS
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
            return 0.0
        except (ValueError, AttributeError):
            return 0.0

    @staticmethod
    def compute_stft(
        audio_data: np.ndarray,
        sample_rate: int = 48000,
        n_fft: int = 2048,
        hop_length: int = 512,
        window: str = "hann",
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Compute Short-Time Fourier Transform for spectrogram generation

        Args:
            audio_data: 1D numpy array of audio samples
            sample_rate: Sampling frequency in Hz
            n_fft: FFT window size (number of samples)
            hop_length: Number of samples between successive frames
            window: Window function to apply (default: 'hann')

        Returns:
            Tuple of (magnitude_spectrogram, frequencies)
            - magnitude_spectrogram: 2D array [time, freq] with dB values
            - frequencies: 1D array of frequency values in Hz
        """
        # Compute STFT
        f, t, Zxx = signal.stft(
            audio_data,
            fs=sample_rate,
            window=window,
            nperseg=n_fft,
            noverlap=n_fft - hop_length,
        )

        # Convert to magnitude (dB scale)
        magnitude = np.abs(Zxx)

        # Avoid log(0) by adding small epsilon
        magnitude_db = 20 * np.log10(magnitude + 1e-10)

        # Transpose to [time, freq] format for easier visualization
        return magnitude_db.T, f

    @staticmethod
    def filter_frequency_range(
        spectrogram: np.ndarray,
        frequencies: np.ndarray,
        freq_min: float,
        freq_max: float,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Filter spectrogram to specific frequency range

        Useful for focusing on voice frequencies (80-8000 Hz)

        Args:
            spectrogram: 2D spectrogram array [time, freq]
            frequencies: 1D array of frequency values in Hz
            freq_min: Minimum frequency to keep (Hz)
            freq_max: Maximum frequency to keep (Hz)

        Returns:
            Tuple of (filtered_spectrogram, filtered_frequencies)
        """
        mask = (frequencies >= freq_min) & (frequencies <= freq_max)
        return spectrogram[:, mask], frequencies[mask]

    @staticmethod
    def compute_stft_slice(
        audio_chunk: np.ndarray,
        sample_rate: int = 48000,
        n_fft: int = 2048,
        freq_min: float = 80.0,
        freq_max: float = 8000.0,
    ) -> Optional[np.ndarray]:
        """Compute single STFT slice for real-time spectrogram updates

        Used during recording to get one frequency-domain slice from a chunk
        of audio samples.

        Args:
            audio_chunk: 1D numpy array of audio samples
            sample_rate: Sampling frequency in Hz
            n_fft: FFT window size
            freq_min: Minimum frequency to keep (Hz)
            freq_max: Maximum frequency to keep (Hz)

        Returns:
            1D array of magnitude values for the frequency range,
            or None if chunk is too small
        """
        # Need at least n_fft samples
        if len(audio_chunk) < n_fft:
            return None

        # Use only the last n_fft samples for this slice
        audio_window = audio_chunk[-n_fft:]

        # Apply Hann window
        window = signal.get_window("hann", n_fft)
        windowed = audio_window * window

        # Compute FFT
        fft_result = np.fft.rfft(windowed, n=n_fft)

        # Get magnitude and convert to dB
        magnitude = np.abs(fft_result)
        magnitude_db = 20 * np.log10(magnitude + 1e-10)

        # Get frequency bins
        frequencies = np.fft.rfftfreq(n_fft, 1.0 / sample_rate)

        # Filter to voice range
        mask = (frequencies >= freq_min) & (frequencies <= freq_max)

        return magnitude_db[mask]
