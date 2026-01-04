from typing import Optional, TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QPointF, QRect, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QWheelEvent,
)
from PySide6.QtWidgets import QWidget

from src.view.style import AppStyle

if TYPE_CHECKING:
    from src.model.viewport_state import ViewportState


class SpectrogramWidget(QWidget):
    """Custom widget for spectrogram visualization

    Displays frequency content over time using a 2D color heatmap.
    Time is shown on the x-axis, frequency on the y-axis, and amplitude
    is represented by color intensity.
    """

    # Signals
    seek_requested = Signal(float)  # Position 0.0-1.0

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize spectrogram widget

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        # Spectrogram data (2D numpy array: [time_bins, freq_bins])
        self._spectrogram_data: Optional[np.ndarray] = None
        self._frequency_bins: Optional[np.ndarray] = None  # Hz values for y-axis
        self._playback_position = 0.0  # 0.0 to 1.0
        self._is_recording = False
        self._is_loading = False
        self._cached_image: Optional[QImage] = None  # Cache rendered image

        # Viewport state (for zoom/pan)
        self._viewport_state: Optional["ViewportState"] = None

        # Mouse interaction tracking
        self._mouse_press_pos: Optional[QPointF] = None
        self._is_dragging = False
        self._drag_start_pan = 0.0

        # Visual settings - use app theme colors
        self._background_color = QColor(AppStyle.get_color("surface"))
        self._grid_color = QColor(AppStyle.get_color("border"))
        self._position_color = QColor(AppStyle.get_color("accent"))
        self._text_color = QColor(AppStyle.get_color("text_primary"))

        # Color map for amplitude (dB scale)
        self._min_db = -80.0  # Minimum dB to display (noise floor)
        self._max_db = 0.0  # Maximum dB (0 dB reference)

        # Set minimum size
        self.setMinimumHeight(150)
        self.setMinimumWidth(400)

        # Enable mouse tracking
        self.setMouseTracking(True)

    def set_spectrogram_data(
        self, data: np.ndarray, freq_bins: Optional[np.ndarray] = None
    ) -> None:
        """Set full spectrogram data (for playback)

        Args:
            data: 2D numpy array [time_bins, freq_bins] with dB values
            freq_bins: 1D array of frequency values in Hz (optional)
        """
        self._spectrogram_data = data
        if freq_bins is not None:
            self._frequency_bins = freq_bins

        # Invalidate cached image when data changes
        self._cached_image = None
        self.update()

    def set_playback_position(self, position: float) -> None:
        """Set playback position indicator

        Args:
            position: Position from 0.0 to 1.0
        """
        self._playback_position = max(0.0, min(1.0, position))
        self.update()

    def set_recording_mode(self, is_recording: bool) -> None:
        """Set recording mode

        Args:
            is_recording: True if currently recording
        """
        self._is_recording = is_recording
        if is_recording:
            self._playback_position = 0.0
        self.update()

    def set_loading_state(self, is_loading: bool) -> None:
        """Set loading state

        Args:
            is_loading: True if loading in progress
        """
        self._is_loading = is_loading
        self.update()

    def set_viewport_state(self, viewport_state: Optional["ViewportState"]) -> None:
        """Set viewport state for zoom/pan functionality

        Args:
            viewport_state: Shared viewport state model
        """
        # Disconnect from old viewport state
        if self._viewport_state:
            try:
                self._viewport_state.viewport_changed.disconnect(self.update)
            except RuntimeError:
                pass  # Already disconnected

        # Connect to new viewport state
        self._viewport_state = viewport_state
        if viewport_state:
            viewport_state.viewport_changed.connect(self.update)

        # Invalidate cache since viewport affects rendering
        self._cached_image = None
        self.update()

    def clear(self) -> None:
        """Clear spectrogram display"""
        self._spectrogram_data = None
        self._frequency_bins = None
        self._playback_position = 0.0
        self._is_recording = False
        self._is_loading = False
        self._cached_image = None  # Clear cache
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Custom paint event for spectrogram rendering

        Args:
            event: Paint event
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background
        painter.fillRect(self.rect(), self._background_color)

        # Draw grid lines
        self._draw_grid(painter)

        # Handle different states
        if self._is_loading:
            self._draw_loading_indicator(painter)
        elif self._spectrogram_data is not None and len(self._spectrogram_data) > 0:
            self._draw_spectrogram(painter)
        elif self._is_recording:
            self._draw_recording_indicator(painter)
        else:
            self._draw_placeholder(painter)

        # Draw playback position
        if self._playback_position > 0.0 and not self._is_recording:
            self._draw_position_indicator(painter)

    def _draw_grid(self, painter: QPainter) -> None:
        """Draw grid lines

        Args:
            painter: QPainter object
        """
        painter.setPen(QPen(self._grid_color, 1, Qt.PenStyle.DotLine))

        # Horizontal lines (frequency markers)
        for i in range(1, 5):
            y = int(self.height() * i / 5)
            painter.drawLine(0, y, self.width(), y)

        # Vertical lines (time markers)
        for i in range(1, 10):
            x = int(self.width() * i / 10)
            painter.drawLine(x, 0, x, self.height())

    def _draw_spectrogram(self, painter: QPainter) -> None:
        """Draw spectrogram as color heatmap (with QImage caching and viewport support)

        Args:
            painter: QPainter object
        """
        if self._spectrogram_data is None or len(self._spectrogram_data) == 0:
            return

        time_bins, freq_bins = self._spectrogram_data.shape

        # Get visible time range based on viewport
        if self._viewport_state:
            # Use floating-point indices to avoid rounding mismatches
            start_bin_float = self._viewport_state.pan_offset * time_bins
            end_bin_float = (self._viewport_state.pan_offset + self._viewport_state.visible_duration) * time_bins

            # Round to nearest integer for consistent behavior
            start_bin = int(round(start_bin_float))
            end_bin = int(round(end_bin_float))

            start_bin = max(0, min(start_bin, time_bins - 1))
            end_bin = max(start_bin + 1, min(end_bin, time_bins))
            visible_data = self._spectrogram_data[start_bin:end_bin, :]
        else:
            visible_data = self._spectrogram_data

        # Check cache validity (size and viewport)
        cache_valid = (
            self._cached_image is not None
            and self._cached_image.width() == self.width()
            and self._cached_image.height() == self.height()
        )

        # For now, invalidate cache on viewport change (can optimize later)
        if self._viewport_state and self._viewport_state.zoom_level != 1.0:
            cache_valid = False

        if cache_valid and self._viewport_state is None:
            painter.drawImage(0, 0, self._cached_image)
            self._draw_frequency_labels(painter)
            return

        # Render visible portion to QImage
        visible_time_bins = visible_data.shape[0]

        # Create image at visible spectrogram resolution
        image = QImage(visible_time_bins, freq_bins, QImage.Format.Format_RGB888)

        # Normalize visible spectrogram data to 0-1 range
        spec_normalized = np.clip(
            (visible_data - self._min_db) / (self._max_db - self._min_db),
            0.0,
            1.0,
        )

        # Fill image with colors based on amplitude
        for t in range(visible_time_bins):
            for f in range(freq_bins):
                amplitude = spec_normalized[t, f]
                color = self._amplitude_to_color(amplitude)
                # Note: Image is drawn bottom-to-top for frequencies (low at bottom)
                image.setPixelColor(t, freq_bins - 1 - f, color)

        # Scale to widget size
        scaled_image = image.scaled(
            self.width(),
            self.height(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        # Cache if no viewport transformation
        if self._viewport_state is None or self._viewport_state.zoom_level == 1.0:
            self._cached_image = scaled_image

        # Draw the image
        painter.drawImage(0, 0, scaled_image)
        self._draw_frequency_labels(painter)

    def _amplitude_to_color(self, amplitude: float) -> QColor:
        """Map normalized amplitude (0-1) to color

        Uses a perceptually uniform gradient:
        Black → Blue → Cyan → Yellow

        Args:
            amplitude: Normalized amplitude from 0.0 (quiet) to 1.0 (loud)

        Returns:
            QColor for the given amplitude
        """
        # Clamp to valid range
        amplitude = max(0.0, min(1.0, amplitude))

        # Multi-stop gradient (inferno/viridis-like)
        if amplitude < 0.25:
            # Black to dark blue
            t = amplitude / 0.25
            r = int(t * 0)
            g = int(t * 0)
            b = int(t * 100)
        elif amplitude < 0.5:
            # Dark blue to cyan
            t = (amplitude - 0.25) / 0.25
            r = int(t * 0)
            g = int(100 + t * 155)
            b = int(100 + t * 155)
        elif amplitude < 0.75:
            # Cyan to yellow
            t = (amplitude - 0.5) / 0.25
            r = int(t * 255)
            g = 255
            b = int(255 - t * 255)
        else:
            # Yellow to white
            t = (amplitude - 0.75) / 0.25
            r = 255
            g = 255
            b = int(t * 255)

        return QColor(r, g, b)

    def _draw_frequency_labels(self, painter: QPainter) -> None:
        """Draw frequency labels on y-axis

        Args:
            painter: QPainter object
        """
        if self._frequency_bins is None or len(self._frequency_bins) == 0:
            return

        painter.setPen(QPen(self._text_color, 1))
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)

        # Draw labels at key frequencies
        freq_labels = [100, 500, 1000, 2000, 4000, 8000]  # Hz

        for freq in freq_labels:
            if freq < self._frequency_bins[0] or freq > self._frequency_bins[-1]:
                continue

            # Find closest frequency bin
            idx = np.argmin(np.abs(self._frequency_bins - freq))

            # Convert to y position (inverted - high freq at top)
            freq_ratio = idx / len(self._frequency_bins)
            y = int(self.height() * (1 - freq_ratio))

            # Draw label
            if freq >= 1000:
                label = f"{freq//1000}k"
            else:
                label = str(freq)

            painter.drawText(5, y - 2, label)

    def _draw_recording_indicator(self, painter: QPainter) -> None:
        """Draw recording indicator

        Args:
            painter: QPainter object
        """
        painter.setPen(QPen(self._position_color, 2))
        font = painter.font()
        font.setPointSize(14)
        painter.setFont(font)

        text = "● RECORDING..."
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)

    def _draw_placeholder(self, painter: QPainter) -> None:
        """Draw placeholder text when no spectrogram

        Args:
            painter: QPainter object
        """
        painter.setPen(QPen(QColor(AppStyle.get_color("text_secondary")), 1))
        font = painter.font()
        font.setPointSize(12)
        painter.setFont(font)

        text = "No audio loaded"
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)

    def _draw_loading_indicator(self, painter: QPainter) -> None:
        """Draw loading indicator

        Args:
            painter: QPainter object
        """
        painter.setPen(QPen(self._text_color, 2))
        font = painter.font()
        font.setPointSize(12)
        painter.setFont(font)

        text = "Computing spectrogram..."
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)

    def _draw_position_indicator(self, painter: QPainter) -> None:
        """Draw playback position indicator with viewport support

        Args:
            painter: QPainter object
        """
        # Use viewport transformation if available
        if self._viewport_state:
            # Only draw if position is visible in viewport
            if not self._viewport_state.is_time_visible(self._playback_position):
                return
            x = int(
                self._viewport_state.time_to_screen(
                    self._playback_position, self.width()
                )
            )
        else:
            x = int(self.width() * self._playback_position)

        # Draw vertical line
        painter.setPen(QPen(self._position_color, 2))
        painter.drawLine(x, 0, x, self.height())

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Handle mouse wheel for zooming

        Args:
            event: Wheel event
        """
        # Don't zoom during recording
        if self._is_recording or not self._viewport_state or self._spectrogram_data is None:
            return

        # Get mouse position in normalized time
        mouse_x = event.position().x()
        center_time = self._viewport_state.screen_to_time(mouse_x, self.width())

        # Zoom in/out based on wheel delta
        delta = event.angleDelta().y()
        zoom_factor = 1.1 if delta > 0 else 1 / 1.1
        new_zoom = np.clip(
            self._viewport_state.zoom_level * zoom_factor, 1.0, 50.0
        )

        self._viewport_state.set_zoom(new_zoom, center_time)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press - track for click vs drag

        Args:
            event: Mouse event
        """
        if event.button() == Qt.MouseButton.LeftButton and self._spectrogram_data is not None:
            self._mouse_press_pos = event.position()
            self._is_dragging = False
            if self._viewport_state:
                self._drag_start_pan = self._viewport_state.pan_offset

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move - detect drag for panning

        Args:
            event: Mouse event
        """
        if self._mouse_press_pos and self._viewport_state:
            # Check if moved enough to be a drag
            delta = event.position() - self._mouse_press_pos
            if not self._is_dragging and delta.manhattanLength() > 5:
                self._is_dragging = True
                self.setCursor(Qt.CursorShape.ClosedHandCursor)

            # Pan if dragging and zoomed in
            if self._is_dragging and self._viewport_state.zoom_level > 1.0:
                # Calculate pan delta in normalized time
                delta_x = delta.x()
                time_delta = (
                    delta_x / self.width()
                ) * self._viewport_state.visible_duration
                new_pan = self._drag_start_pan - time_delta
                self._viewport_state.set_pan(new_pan)
                event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release - seek if not dragged

        Args:
            event: Mouse event
        """
        if event.button() == Qt.MouseButton.LeftButton:
            # Only seek if it was a click (not drag)
            if not self._is_dragging and self._viewport_state:
                position = self._viewport_state.screen_to_time(
                    event.position().x(), self.width()
                )
                self.seek_requested.emit(position)

            # Reset state
            self._mouse_press_pos = None
            self._is_dragging = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Handle double-click to reset zoom

        Args:
            event: Mouse event
        """
        if event.button() == Qt.MouseButton.LeftButton and self._viewport_state:
            self._viewport_state.reset()
            event.accept()

    def resizeEvent(self, event) -> None:
        """Handle widget resize - invalidate cached image

        Args:
            event: Resize event
        """
        super().resizeEvent(event)
        # Invalidate cache on resize so it gets regenerated at new size
        self._cached_image = None
