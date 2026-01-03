from typing import Optional

import numpy as np
from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import QWidget

from src.view.style import AppStyle


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

    def clear(self) -> None:
        """Clear spectrogram display"""
        self._spectrogram_data = None
        self._frequency_bins = None
        self._playback_position = 0.0
        self._is_recording = False
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

        # Draw spectrogram or placeholder
        if self._spectrogram_data is not None and len(self._spectrogram_data) > 0:
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
        """Draw spectrogram as color heatmap

        Args:
            painter: QPainter object
        """
        if self._spectrogram_data is None or len(self._spectrogram_data) == 0:
            return

        width = self.width()
        height = self.height()

        time_bins, freq_bins = self._spectrogram_data.shape

        # Create QImage for efficient rendering
        # We'll draw the spectrogram as an image and scale it to fit
        image = QImage(time_bins, freq_bins, QImage.Format.Format_RGB888)

        # Normalize spectrogram data to 0-1 range for color mapping
        spec_normalized = np.clip(
            (self._spectrogram_data - self._min_db) / (self._max_db - self._min_db),
            0.0,
            1.0,
        )

        # Fill image with colors based on amplitude
        for t in range(time_bins):
            for f in range(freq_bins):
                amplitude = spec_normalized[t, f]
                color = self._amplitude_to_color(amplitude)
                # Note: Image is drawn bottom-to-top for frequencies (low at bottom)
                image.setPixelColor(t, freq_bins - 1 - f, color)

        # Draw the image scaled to widget size
        target_rect = QRect(0, 0, width, height)
        painter.drawImage(target_rect, image)

        # Draw frequency labels
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

    def _draw_position_indicator(self, painter: QPainter) -> None:
        """Draw playback position indicator

        Args:
            painter: QPainter object
        """
        x = int(self.width() * self._playback_position)

        # Draw vertical line
        painter.setPen(QPen(self._position_color, 2))
        painter.drawLine(x, 0, x, self.height())

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press for seeking

        Args:
            event: Mouse event
        """
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._spectrogram_data is not None
        ):
            position = event.position().x() / self.width()
            self.seek_requested.emit(position)
