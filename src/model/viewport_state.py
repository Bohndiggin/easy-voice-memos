from typing import Optional

import numpy as np
from PySide6.QtCore import QObject, Signal


class ViewportState(QObject):
    """Shared zoom/pan state for waveform and spectrogram visualizations

    Manages the viewport transformation for synchronized zoom and pan across
    both visualization widgets. Uses normalized time coordinates (0.0-1.0)
    for resolution-independent transformations.
    """

    # Signals
    viewport_changed = Signal()  # Emitted when zoom or pan changes
    zoom_level_changed = Signal(float)  # Emitted when zoom crosses resolution threshold

    def __init__(self, parent: Optional[QObject] = None):
        """Initialize viewport state

        Args:
            parent: Parent QObject
        """
        super().__init__(parent)

        # Zoom/pan state (normalized 0.0-1.0 coordinates)
        self._zoom_level = 1.0  # 1.0 = fit all, 50.0 = max zoom
        self._pan_offset = 0.0  # 0.0 = left edge at start, 1.0 = left edge at end

        # Constants
        self._min_zoom = 1.0
        self._max_zoom = 50.0

    @property
    def zoom_level(self) -> float:
        """Get current zoom level

        Returns:
            Zoom level (1.0 = fit-all, higher = more zoomed in)
        """
        return self._zoom_level

    @property
    def pan_offset(self) -> float:
        """Get current pan offset

        Returns:
            Pan offset in normalized coordinates (0.0-1.0)
        """
        return self._pan_offset

    @property
    def visible_duration(self) -> float:
        """Get fraction of total duration visible in viewport

        Returns:
            Visible duration as fraction (0.0-1.0)
        """
        return min(1.0, 1.0 / self._zoom_level)

    def set_zoom(self, zoom: float, center_time: float = 0.5) -> None:
        """Set zoom level while keeping a time point centered

        Args:
            zoom: New zoom level (will be clamped to min/max)
            center_time: Normalized time (0.0-1.0) to keep at same screen position
        """
        # Clamp zoom to valid range
        new_zoom = np.clip(zoom, self._min_zoom, self._max_zoom)

        if new_zoom == self._zoom_level:
            return  # No change

        # Check if we're crossing resolution thresholds
        old_resolution_tier = self._get_resolution_tier(self._zoom_level)
        new_resolution_tier = self._get_resolution_tier(new_zoom)

        # Calculate new visible duration
        new_visible_duration = 1.0 / new_zoom

        # Calculate position of center_time in current viewport (0.0-1.0 of viewport width)
        if self.visible_duration > 0:
            center_viewport_pos = (center_time - self._pan_offset) / self.visible_duration
            center_viewport_pos = np.clip(center_viewport_pos, 0.0, 1.0)
        else:
            center_viewport_pos = 0.5

        # Calculate new pan offset to keep center_time at same viewport position
        new_pan_offset = center_time - (center_viewport_pos * new_visible_duration)

        # Update state
        self._zoom_level = new_zoom
        self._pan_offset = np.clip(new_pan_offset, 0.0, max(0.0, 1.0 - new_visible_duration))

        self.viewport_changed.emit()

        # Emit zoom level changed if we crossed a resolution threshold
        if old_resolution_tier != new_resolution_tier:
            self.zoom_level_changed.emit(new_zoom)

    def _get_resolution_tier(self, zoom: float) -> int:
        """Get resolution tier for a given zoom level

        Args:
            zoom: Zoom level

        Returns:
            Resolution tier (0-3)
        """
        if zoom < 2.0:
            return 0  # 1000 samples
        elif zoom < 5.0:
            return 1  # 2000 samples
        elif zoom < 10.0:
            return 2  # 5000 samples
        else:
            return 3  # 10000 samples

    def get_recommended_resolution(self) -> int:
        """Get recommended waveform resolution for current zoom level

        Returns waveform resolution that's compatible with spectrogram bins
        to avoid rounding mismatches. The waveform resolution is a multiple
        of the expected spectrogram bins for alignment.

        Returns:
            Number of samples to extract
        """
        tier = self._get_resolution_tier(self._zoom_level)
        # Calculate expected spectrogram bins for each hop_length
        # For 5s at 16kHz = 80000 samples:
        # hop_length=1024: ~78 bins, waveform = 78*13 = 1014
        # hop_length=512:  ~156 bins, waveform = 156*13 = 2028
        # hop_length=256:  ~312 bins, waveform = 312*16 = 4992
        # hop_length=128:  ~624 bins, waveform = 624*16 = 9984
        resolutions = [1014, 2028, 4992, 9984]
        return resolutions[tier]

    def get_recommended_hop_length(self) -> int:
        """Get recommended STFT hop length for current zoom level

        Smaller hop length = better temporal resolution for spectrogram

        Returns:
            Hop length in samples
        """
        tier = self._get_resolution_tier(self._zoom_level)
        # hop_length values for ~64ms, ~32ms, ~16ms, ~8ms at 16kHz
        hop_lengths = [1024, 512, 256, 128]
        return hop_lengths[tier]

    def set_pan(self, offset: float) -> None:
        """Set pan offset with bounds checking

        Args:
            offset: New pan offset in normalized coordinates (0.0-1.0)
        """
        # Clamp to valid range (can't pan beyond edges)
        max_offset = max(0.0, 1.0 - self.visible_duration)
        new_offset = np.clip(offset, 0.0, max_offset)

        if new_offset == self._pan_offset:
            return  # No change

        self._pan_offset = new_offset
        self.viewport_changed.emit()

    def reset(self) -> None:
        """Reset to fit-all view (zoom=1.0, pan=0.0)"""
        if self._zoom_level == 1.0 and self._pan_offset == 0.0:
            return  # Already reset

        self._zoom_level = 1.0
        self._pan_offset = 0.0
        self.viewport_changed.emit()

    def get_visible_time_range(self) -> tuple[float, float]:
        """Get the exact visible time range as normalized coordinates

        Returns:
            Tuple of (start_time, end_time) in normalized coordinates (0.0-1.0)
        """
        start_time = self._pan_offset
        end_time = min(1.0, self._pan_offset + self.visible_duration)
        return (start_time, end_time)

    def screen_to_time(self, pixel_x: float, widget_width: float) -> float:
        """Convert screen coordinate to normalized time

        Args:
            pixel_x: X coordinate in screen pixels
            widget_width: Widget width in pixels

        Returns:
            Normalized time (0.0-1.0)
        """
        if widget_width <= 0:
            return 0.0

        # Map screen pixel to viewport fraction (0.0-1.0)
        viewport_fraction = pixel_x / widget_width

        # Map viewport fraction to normalized time
        normalized_time = self._pan_offset + viewport_fraction * self.visible_duration

        return np.clip(normalized_time, 0.0, 1.0)

    def time_to_screen(self, normalized_time: float, widget_width: float) -> float:
        """Convert normalized time to screen coordinate

        Args:
            normalized_time: Time in normalized coordinates (0.0-1.0)
            widget_width: Widget width in pixels

        Returns:
            X coordinate in screen pixels
        """
        if self.visible_duration <= 0:
            return 0.0

        # Map normalized time to viewport fraction
        viewport_fraction = (normalized_time - self._pan_offset) / self.visible_duration

        # Map viewport fraction to screen pixel
        pixel_x = viewport_fraction * widget_width

        return pixel_x

    def is_time_visible(self, normalized_time: float) -> bool:
        """Check if a time point is visible in the current viewport

        Args:
            normalized_time: Time in normalized coordinates (0.0-1.0)

        Returns:
            True if the time point is visible
        """
        return self._pan_offset <= normalized_time <= (self._pan_offset + self.visible_duration)
