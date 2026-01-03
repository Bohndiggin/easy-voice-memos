from typing import Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.model.codec_config import CodecPresets
from src.model.settings import AppSettings
from src.view.style import AppStyle


class RecordingPanel(QWidget):
    """Recording controls panel widget"""

    # Signals
    record_clicked = Signal()
    pause_clicked = Signal()
    stop_clicked = Signal()
    settings_clicked = Signal()
    preset_changed = Signal(str)  # preset name
    device_changed = Signal(object)  # QAudioDevice

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        app_settings: Optional[AppSettings] = None,
    ):
        """Initialize recording panel

        Args:
            parent: Parent widget
            app_settings: Application settings instance
        """
        super().__init__(parent)

        self._is_recording = False
        self._is_paused = False
        self._app_settings = app_settings

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup UI components"""
        layout = QVBoxLayout(self)

        # Group box
        group = QGroupBox("Recording")
        group_layout = QVBoxLayout()

        # Button row
        button_layout = QHBoxLayout()

        # Record button
        self._record_btn = QPushButton("Record")
        self._record_btn.setObjectName("recordButton")
        self._record_btn.clicked.connect(self._on_record_clicked)
        button_layout.addWidget(self._record_btn)

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

        # Timer and VU meter row
        status_layout = QHBoxLayout()

        # Timer label
        timer_label = QLabel("Time:")
        status_layout.addWidget(timer_label)

        self._timer_label = QLabel("00:00")
        self._timer_label.setObjectName("timerLabel")
        status_layout.addWidget(self._timer_label)

        status_layout.addStretch()

        # VU meter label
        vu_label = QLabel("Level:")
        status_layout.addWidget(vu_label)

        # VU meter (progress bar)
        self._vu_meter = QProgressBar()
        self._vu_meter.setMaximum(100)
        self._vu_meter.setValue(0)
        self._vu_meter.setTextVisible(False)
        self._vu_meter.setMaximumWidth(150)
        self._vu_meter.setMaximumHeight(20)
        status_layout.addWidget(self._vu_meter)

        group_layout.addLayout(status_layout)

        # Preset selection row
        preset_layout = QHBoxLayout()

        preset_label = QLabel("Preset:")
        preset_layout.addWidget(preset_label)

        self._preset_combo = QComboBox()
        self._populate_presets()
        self._preset_combo.currentTextChanged.connect(self._on_preset_changed)
        preset_layout.addWidget(self._preset_combo)

        # Settings button
        self._settings_btn = QPushButton("Advanced...")
        self._settings_btn.clicked.connect(self._on_settings_clicked)
        preset_layout.addWidget(self._settings_btn)

        preset_layout.addStretch()
        group_layout.addLayout(preset_layout)

        # Audio input device selection row
        device_layout = QHBoxLayout()

        device_label = QLabel("Input Device:")
        device_layout.addWidget(device_label)

        self._device_combo = QComboBox()
        self._populate_audio_devices()
        self._device_combo.currentIndexChanged.connect(self._on_device_changed)
        device_layout.addWidget(self._device_combo)

        device_layout.addStretch()
        group_layout.addLayout(device_layout)

        group.setLayout(group_layout)
        layout.addWidget(group)

    def _populate_presets(self) -> None:
        """Populate preset combo box with built-in and custom presets"""
        # Get all presets (built-in + custom)
        if self._app_settings:
            presets = self._app_settings.get_all_presets()
        else:
            presets = CodecPresets.get_all_presets()

        for preset_name in presets.keys():
            self._preset_combo.addItem(preset_name)

        # Set default to "Voice - Standard"
        index = self._preset_combo.findText("Voice - Standard")
        if index >= 0:
            self._preset_combo.setCurrentIndex(index)

    def _populate_audio_devices(self) -> None:
        """Populate audio input device combo box"""

        self._device_combo.clear()

        # Get all audio input devices
        devices = QMediaDevices.audioInputs()

        if not devices:
            self._device_combo.addItem("No input devices found", None)
            return

        # Add devices to combo box
        for device in devices:
            # Store the device object as user data
            self._device_combo.addItem(device.description(), device)

        # Select default device
        default_device = QMediaDevices.defaultAudioInput()
        if default_device:
            for i in range(self._device_combo.count()):
                device = self._device_combo.itemData(i)
                if device and device.id() == default_device.id():
                    self._device_combo.setCurrentIndex(i)
                    break

    def _on_record_clicked(self) -> None:
        """Handle record button click"""
        self.record_clicked.emit()

    def _on_pause_clicked(self) -> None:
        """Handle pause button click"""
        self.pause_clicked.emit()

    def _on_stop_clicked(self) -> None:
        """Handle stop button click"""
        self.stop_clicked.emit()

    def _on_settings_clicked(self) -> None:
        """Handle settings button click"""
        self.settings_clicked.emit()

    def _on_preset_changed(self, preset_name: str) -> None:
        """Handle preset change"""
        self.preset_changed.emit(preset_name)

    def _on_device_changed(self, index: int) -> None:
        """Handle audio device change"""
        device = self._device_combo.itemData(index)
        if device:
            self.device_changed.emit(device)

    def get_selected_device(self):
        """Get currently selected audio device

        Returns:
            QAudioDevice or None
        """
        return self._device_combo.currentData()

    def set_recording_state(self, is_recording: bool) -> None:
        """Set recording state

        Args:
            is_recording: True if recording
        """
        self._is_recording = is_recording

        if is_recording:
            self._record_btn.setText("Recording...")
            self._record_btn.setEnabled(False)
            self._pause_btn.setEnabled(True)
            self._stop_btn.setEnabled(True)
            self._preset_combo.setEnabled(False)
            self._settings_btn.setEnabled(False)
        else:
            self._record_btn.setText("Record")
            self._record_btn.setEnabled(True)
            self._pause_btn.setEnabled(False)
            self._pause_btn.setText("Pause")
            self._stop_btn.setEnabled(False)
            self._preset_combo.setEnabled(True)
            self._settings_btn.setEnabled(True)
            self._is_paused = False

    def set_paused_state(self, is_paused: bool) -> None:
        """Set paused state

        Args:
            is_paused: True if paused
        """
        self._is_paused = is_paused

        if is_paused:
            self._pause_btn.setText("Resume")
            self._record_btn.setText("Paused")
        else:
            self._pause_btn.setText("Pause")
            self._record_btn.setText("Recording...")

    def update_timer(self, duration: float) -> None:
        """Update timer display

        Args:
            duration: Duration in seconds
        """
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)

        if hours > 0:
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            time_str = f"{minutes:02d}:{seconds:02d}"

        self._timer_label.setText(time_str)

    def update_audio_level(self, level: float) -> None:
        """Update VU meter

        Args:
            level: Audio level from 0.0 to 1.0
        """
        value = int(level * 100)
        self._vu_meter.setValue(value)

        # Change color based on level
        if value > 90:
            # Red for clipping
            self._vu_meter.setStyleSheet(
                f"QProgressBar::chunk {{ background-color: {AppStyle.get_color('error')}; }}"
            )
        elif value > 70:
            # Orange for high
            self._vu_meter.setStyleSheet(
                f"QProgressBar::chunk {{ background-color: {AppStyle.get_color('accent')}; }}"
            )
        else:
            # Normal color
            self._vu_meter.setStyleSheet(
                f"QProgressBar::chunk {{ background-color: {AppStyle.get_color('success')}; }}"
            )

    def get_selected_preset(self) -> str:
        """Get selected preset name

        Returns:
            Preset name
        """
        return self._preset_combo.currentText()

    def set_selected_preset(self, preset_name: str) -> None:
        """Set selected preset

        Args:
            preset_name: Preset name
        """
        index = self._preset_combo.findText(preset_name)
        if index >= 0:
            self._preset_combo.setCurrentIndex(index)

    def reset(self) -> None:
        """Reset panel to initial state"""
        self.set_recording_state(False)
        self.update_timer(0.0)
        self.update_audio_level(0.0)
