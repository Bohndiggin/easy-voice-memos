from typing import Optional

import numpy as np
from PySide6.QtCore import QPointF, QRect, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from src.view.style import AppStyle


class WaveformWidget(QWidget):
    """Custom widget for waveform visualization"""

    # Signals
    seek_requested = Signal(float)  # Position 0.0-1.0

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize waveform widget

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        # Waveform data
        self._waveform_data: Optional[np.ndarray] = None
        self._playback_position = 0.0  # 0.0 to 1.0
        self._is_recording = False
        self._recording_buffer: Optional[np.ndarray] = None  # Live recording data

        # Visual settings
        self._bar_color = QColor(AppStyle.get_color("primary"))
        self._background_color = QColor(AppStyle.get_color("surface"))
        self._position_color = QColor(AppStyle.get_color("accent"))
        self._grid_color = QColor(AppStyle.get_color("border"))

        # Set minimum size
        self.setMinimumHeight(120)
        self.setMinimumWidth(400)

        # Enable mouse tracking
        self.setMouseTracking(True)

    def set_waveform_data(self, data: Optional[np.ndarray]) -> None:
        """Set waveform data to display

        Args:
            data: Numpy array of amplitude values
        """
        self._waveform_data = data
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
            self._waveform_data = None
            self._recording_buffer = None
        else:
            self._recording_buffer = None
        self.update()

    def set_recording_buffer(self, data: Optional[np.ndarray]) -> None:
        """Set live recording buffer for real-time visualization

        Args:
            data: Numpy array of recent audio levels
        """
        self._recording_buffer = data
        self.update()

    def clear(self) -> None:
        """Clear waveform display"""
        self._waveform_data = None
        self._playback_position = 0.0
        self._is_recording = False
        self._recording_buffer = None
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Custom paint event for waveform rendering

        Args:
            event: Paint event
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background
        painter.fillRect(self.rect(), self._background_color)

        # Draw grid lines
        self._draw_grid(painter)

        # Draw waveform
        if self._waveform_data is not None and len(self._waveform_data) > 0:
            self._draw_waveform(painter)
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

        # Horizontal center line
        center_y = self.height() // 2
        painter.drawLine(0, center_y, self.width(), center_y)

        # Vertical lines (time markers)
        for i in range(1, 10):
            x = int(self.width() * i / 10)
            painter.drawLine(x, 0, x, self.height())

    def _draw_waveform(self, painter: QPainter) -> None:
        """Draw waveform bars

        Args:
            painter: QPainter object
        """
        if self._waveform_data is None or len(self._waveform_data) == 0:
            return

        width = self.width()
        height = self.height()
        center_y = height / 2

        # Calculate bar width
        num_bars = len(self._waveform_data)
        bar_width = max(1, width / num_bars)
        spacing = max(0, bar_width * 0.2) if bar_width > 2 else 0
        actual_bar_width = max(1, bar_width - spacing)

        # Normalize waveform data
        max_amplitude = (
            np.max(self._waveform_data) if np.max(self._waveform_data) > 0 else 1.0
        )
        normalized = self._waveform_data / max_amplitude

        # Draw bars
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self._bar_color))

        for i, amplitude in enumerate(normalized):
            x = i * bar_width
            bar_height = amplitude * (height / 2) * 0.9  # 90% of half height

            # Draw bar (centered vertically)
            rect = QRect(
                int(x),
                int(center_y - bar_height),
                int(actual_bar_width),
                int(bar_height * 2),
            )
            painter.drawRect(rect)

    def _draw_recording_indicator(self, painter: QPainter) -> None:
        """Draw recording indicator with live waveform if available

        Args:
            painter: QPainter object
        """
        # If we have recording buffer data, draw it as a live waveform
        if self._recording_buffer is not None and len(self._recording_buffer) > 0:
            # Use the same drawing logic as regular waveform
            width = self.width()
            height = self.height()
            center_y = height / 2

            # Calculate bar width
            num_bars = len(self._recording_buffer)
            bar_width = max(1, width / num_bars)
            spacing = max(0, bar_width * 0.2) if bar_width > 2 else 0
            actual_bar_width = max(1, bar_width - spacing)

            # Use recording buffer directly (already normalized 0-1)
            normalized = self._recording_buffer

            # Draw bars with accent color for recording
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(
                QBrush(self._position_color)
            )  # Orange/accent color for recording

            for i, amplitude in enumerate(normalized):
                x = i * bar_width
                bar_height = amplitude * (height / 2) * 0.9  # 90% of half height

                # Draw bar (centered vertically)
                rect = QRect(
                    int(x),
                    int(center_y - bar_height),
                    int(actual_bar_width),
                    int(bar_height * 2),
                )
                painter.drawRect(rect)
        else:
            # No data yet, show text indicator
            painter.setPen(QPen(self._bar_color, 2))
            font = painter.font()
            font.setPointSize(14)
            painter.setFont(font)

            text = "● RECORDING..."
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)

    def _draw_placeholder(self, painter: QPainter) -> None:
        """Draw placeholder text when no waveform

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

        # Draw triangle at top
        triangle_size = 8
        points = [
            QPointF(x, 0),
            QPointF(x - triangle_size, triangle_size),
            QPointF(x + triangle_size, triangle_size),
        ]
        painter.setBrush(QBrush(self._position_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(points)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press for seeking

        Args:
            event: Mouse event
        """
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._waveform_data is not None
        ):
            position = event.position().x() / self.width()
            self.seek_requested.emit(position)

    def get_waveform_data(self) -> Optional[np.ndarray]:
        """Get current waveform data

        Returns:
            Waveform data array or None
        """
        return self._waveform_data

    def get_playback_position(self) -> float:
        """Get current playback position

        Returns:
            Position from 0.0 to 1.0
        """
        return self._playback_position
