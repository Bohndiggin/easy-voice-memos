from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from src.view.style import AppStyle


class PlaybackWidget(QWidget):
    """Playback controls widget"""

    # Signals
    play_clicked = Signal()
    pause_clicked = Signal()
    stop_clicked = Signal()
    seek_requested = Signal(int)  # position in milliseconds
    volume_changed = Signal(float)  # 0.0 to 1.0

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize playback widget

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self._is_playing = False
        self._duration = 0
        self._is_seeking = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup UI components"""
        layout = QVBoxLayout(self)

        # Group box
        group = QGroupBox("Playback")
        group_layout = QVBoxLayout()

        # Button row
        button_layout = QHBoxLayout()

        # Play button
        self._play_btn = QPushButton("Play")
        self._play_btn.clicked.connect(self._on_play_clicked)
        self._play_btn.setEnabled(False)
        button_layout.addWidget(self._play_btn)

        # Pause button
        self._pause_btn = QPushButton("Pause")
        self._pause_btn.clicked.connect(self._on_pause_clicked)
        self._pause_btn.setEnabled(False)
        button_layout.addWidget(self._pause_btn)

        # Stop button
        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setObjectName("stopButton")
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        self._stop_btn.setEnabled(False)
        button_layout.addWidget(self._stop_btn)

        button_layout.addStretch()
        group_layout.addLayout(button_layout)

        # Timeline row
        timeline_layout = QHBoxLayout()

        # Current time
        self._current_time_label = QLabel("00:00")
        timeline_layout.addWidget(self._current_time_label)

        # Timeline slider
        self._timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self._timeline_slider.setMinimum(0)
        self._timeline_slider.setMaximum(0)
        self._timeline_slider.setValue(0)
        self._timeline_slider.sliderPressed.connect(self._on_slider_pressed)
        self._timeline_slider.sliderReleased.connect(self._on_slider_released)
        self._timeline_slider.sliderMoved.connect(self._on_slider_moved)
        timeline_layout.addWidget(self._timeline_slider)

        # Total time
        self._total_time_label = QLabel("00:00")
        timeline_layout.addWidget(self._total_time_label)

        group_layout.addLayout(timeline_layout)

        # Volume row
        volume_layout = QHBoxLayout()

        volume_label = QLabel("Volume:")
        volume_layout.addWidget(volume_label)

        # Volume slider
        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setMinimum(0)
        self._volume_slider.setMaximum(100)
        self._volume_slider.setValue(70)
        self._volume_slider.setMaximumWidth(150)
        self._volume_slider.valueChanged.connect(self._on_volume_changed)
        volume_layout.addWidget(self._volume_slider)

        # Volume percentage
        self._volume_label = QLabel("70%")
        volume_layout.addWidget(self._volume_label)

        volume_layout.addStretch()
        group_layout.addLayout(volume_layout)

        group.setLayout(group_layout)
        layout.addWidget(group)

    def _on_play_clicked(self) -> None:
        """Handle play button click"""
        self.play_clicked.emit()

    def _on_pause_clicked(self) -> None:
        """Handle pause button click"""
        self.pause_clicked.emit()

    def _on_stop_clicked(self) -> None:
        """Handle stop button click"""
        self.stop_clicked.emit()

    def _on_slider_pressed(self) -> None:
        """Handle slider press"""
        self._is_seeking = True

    def _on_slider_released(self) -> None:
        """Handle slider release"""
        self._is_seeking = False
        position = self._timeline_slider.value()
        self.seek_requested.emit(position)

    def _on_slider_moved(self, value: int) -> None:
        """Handle slider movement

        Args:
            value: Slider value in milliseconds
        """
        # Update time label while dragging
        self._current_time_label.setText(self._format_time(value))

    def _on_volume_changed(self, value: int) -> None:
        """Handle volume change

        Args:
            value: Volume value 0-100
        """
        self._volume_label.setText(f"{value}%")
        self.volume_changed.emit(value / 100.0)

    def set_playback_state(self, is_playing: bool) -> None:
        """Set playback state

        Args:
            is_playing: True if playing
        """
        self._is_playing = is_playing

        if is_playing:
            self._play_btn.setText("Playing...")
            self._play_btn.setEnabled(False)
            self._pause_btn.setEnabled(True)
            self._stop_btn.setEnabled(True)
        else:
            self._play_btn.setText("Play")
            self._play_btn.setEnabled(True)
            self._pause_btn.setEnabled(False)
            self._stop_btn.setEnabled(False)

    def update_position(self, position_ms: int) -> None:
        """Update playback position

        Args:
            position_ms: Position in milliseconds
        """
        if not self._is_seeking:
            self._timeline_slider.setValue(position_ms)
            self._current_time_label.setText(self._format_time(position_ms))

    def update_duration(self, duration_ms: int) -> None:
        """Update total duration

        Args:
            duration_ms: Duration in milliseconds
        """
        self._duration = duration_ms
        self._timeline_slider.setMaximum(duration_ms)
        self._total_time_label.setText(self._format_time(duration_ms))

    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable playback controls

        Args:
            enabled: True to enable
        """
        self._play_btn.setEnabled(enabled)
        self._timeline_slider.setEnabled(enabled)

        if not enabled:
            self._pause_btn.setEnabled(False)
            self._stop_btn.setEnabled(False)

    def reset(self) -> None:
        """Reset to initial state"""
        self.set_playback_state(False)
        self.update_position(0)
        self.update_duration(0)
        self.set_enabled(False)

    def get_volume(self) -> float:
        """Get current volume level

        Returns:
            Volume from 0.0 to 1.0
        """
        return self._volume_slider.value() / 100.0

    def set_volume(self, level: float) -> None:
        """Set volume level

        Args:
            level: Volume from 0.0 to 1.0
        """
        value = int(level * 100)
        self._volume_slider.setValue(value)

    @staticmethod
    def _format_time(milliseconds: int) -> str:
        """Format time in milliseconds to MM:SS

        Args:
            milliseconds: Time in milliseconds

        Returns:
            Formatted time string
        """
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60

        if minutes >= 60:
            hours = minutes // 60
            minutes = minutes % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        return f"{minutes:02d}:{seconds:02d}"
