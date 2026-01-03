import pickle
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

from src.utils.ffmpeg_wrapper import FFmpegWrapper


class WaveformData:
    """Extracts and caches waveform data for visualization"""

    def __init__(self, audio_file: Path):
        """Initialize waveform data extractor

        Args:
            audio_file: Path to audio file
        """
        self.audio_file = Path(audio_file)
        self._ffmpeg = FFmpegWrapper()
        self._waveform: Optional[np.ndarray] = None
        self._resolution = 1000

    def extract_waveform(self, resolution: int = 1000) -> Optional[np.ndarray]:
        """Extract waveform amplitude data from audio file

        Args:
            resolution: Number of sample points (default: 1000)

        Returns:
            Numpy array of amplitude values or None if failed
        """
        if not self.audio_file.exists():
            return None

        self._resolution = resolution

        # Try to load from cache first
        cached = self.load_from_cache()
        if cached is not None and len(cached) == resolution:
            self._waveform = cached
            return self._waveform

        # Extract using FFmpeg
        waveform = self._ffmpeg.extract_waveform_data(
            self.audio_file, resolution=resolution
        )

        if waveform is not None:
            self._waveform = waveform
            self.cache_waveform()

        return waveform

    def get_peak_levels(self) -> Tuple[float, float]:
        """Get minimum and maximum amplitude levels

        Returns:
            Tuple of (min_level, max_level)
        """
        if self._waveform is None:
            self.extract_waveform()

        if self._waveform is None or len(self._waveform) == 0:
            return (0.0, 0.0)

        return (float(np.min(self._waveform)), float(np.max(self._waveform)))

    def cache_waveform(self) -> bool:
        """Cache waveform data to file

        Returns:
            True if cached successfully
        """
        if self._waveform is None:
            return False

        try:
            cache_path = self._get_cache_path()
            cache_path.parent.mkdir(parents=True, exist_ok=True)

            with open(cache_path, "wb") as f:
                pickle.dump(
                    {"waveform": self._waveform, "resolution": self._resolution}, f
                )

            return True

        except Exception as e:
            print(f"Warning: Failed to cache waveform: {e}")
            return False

    def load_from_cache(self) -> Optional[np.ndarray]:
        """Load waveform data from cache

        Returns:
            Cached waveform array or None if not found
        """
        try:
            cache_path = self._get_cache_path()

            if not cache_path.exists():
                return None

            # Check if cache is newer than audio file
            if cache_path.stat().st_mtime < self.audio_file.stat().st_mtime:
                # Audio file was modified after cache, invalidate cache
                return None

            with open(cache_path, "rb") as f:
                data = pickle.load(f)
                return data.get("waveform")

        except Exception as e:
            print(f"Warning: Failed to load cached waveform: {e}")
            return None

    def _get_cache_path(self) -> Path:
        """Get path to cache file

        Returns:
            Path to cache file
        """
        cache_dir = self.audio_file.parent / ".waveform_cache"
        cache_file = f"{self.audio_file.stem}.wfcache"
        return cache_dir / cache_file

    def clear_cache(self) -> bool:
        """Delete cached waveform data

        Returns:
            True if deleted successfully
        """
        try:
            cache_path = self._get_cache_path()
            if cache_path.exists():
                cache_path.unlink()
            return True
        except Exception as e:
            print(f"Warning: Failed to clear cache: {e}")
            return False

    def get_waveform(self) -> Optional[np.ndarray]:
        """Get current waveform data

        Returns:
            Waveform array or None
        """
        return self._waveform

    def normalize_waveform(self, target_max: float = 1.0) -> Optional[np.ndarray]:
        """Normalize waveform to target maximum amplitude

        Args:
            target_max: Target maximum amplitude (default: 1.0)

        Returns:
            Normalized waveform array or None
        """
        if self._waveform is None:
            self.extract_waveform()

        if self._waveform is None or len(self._waveform) == 0:
            return None

        current_max = np.max(self._waveform)
        if current_max == 0:
            return self._waveform

        normalized = (self._waveform / current_max) * target_max
        return normalized

    @staticmethod
    def extract_from_file(
        file_path: Path, resolution: int = 1000
    ) -> Optional[np.ndarray]:
        """Static method to extract waveform from file

        Args:
            file_path: Path to audio file
            resolution: Number of sample points

        Returns:
            Waveform array or None if failed
        """
        extractor = WaveformData(file_path)
        return extractor.extract_waveform(resolution)

    @staticmethod
    def clear_all_caches(directory: Path) -> int:
        """Clear all waveform caches in a directory

        Args:
            directory: Directory to search for caches

        Returns:
            Number of cache files deleted
        """
        count = 0
        cache_dir = directory / ".waveform_cache"

        if cache_dir.exists():
            try:
                for cache_file in cache_dir.glob("*.wfcache"):
                    cache_file.unlink()
                    count += 1

                # Remove cache directory if empty
                if not any(cache_dir.iterdir()):
                    cache_dir.rmdir()

            except Exception as e:
                print(f"Warning: Failed to clear caches: {e}")

        return count
