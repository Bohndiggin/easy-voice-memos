from typing import Optional, TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QPointF, QRect, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QMouseEvent, QPainter, QPaintEvent, QPen, QWheelEvent
from PySide6.QtWidgets import QWidget

from src.view.style import AppStyle

if TYPE_CHECKING:
    from src.model.viewport_state import ViewportState


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

        # Viewport state (for zoom/pan)
        self._viewport_state: Optional["ViewportState"] = None

        # Mouse interaction tracking
        self._mouse_press_pos: Optional[QPointF] = None
        self._is_dragging = False
        self._drag_start_pan = 0.0

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
        """Draw waveform bars with viewport support

        Args:
            painter: QPainter object
        """
        if self._waveform_data is None or len(self._waveform_data) == 0:
            return

        width = self.width()
        height = self.height()
        center_y = height / 2

        # Get visible data range based on viewport
        total_bars = len(self._waveform_data)
        if self._viewport_state:
            # Use floating-point indices to avoid rounding mismatches
            start_idx_float = self._viewport_state.pan_offset * total_bars
            end_idx_float = (self._viewport_state.pan_offset + self._viewport_state.visible_duration) * total_bars

            # Round to nearest integer for consistent behavior
            start_idx = int(round(start_idx_float))
            end_idx = int(round(end_idx_float))

            start_idx = max(0, min(start_idx, total_bars - 1))
            end_idx = max(start_idx + 1, min(end_idx, total_bars))
            visible_data = self._waveform_data[start_idx:end_idx]
        else:
            visible_data = self._waveform_data

        # Calculate bar width based on visible data
        num_bars = len(visible_data)
        if num_bars == 0:
            return

        bar_width = max(1, width / num_bars)
        spacing = max(0, bar_width * 0.2) if bar_width > 2 else 0
        actual_bar_width = max(1, bar_width - spacing)

        # Normalize waveform data
        max_amplitude = (
            np.max(self._waveform_data) if np.max(self._waveform_data) > 0 else 1.0
        )
        normalized = visible_data / max_amplitude

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

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Handle mouse wheel for zooming

        Args:
            event: Wheel event
        """
        # Don't zoom during recording
        if self._is_recording or not self._viewport_state or self._waveform_data is None:
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
        if event.button() == Qt.MouseButton.LeftButton and self._waveform_data is not None:
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
