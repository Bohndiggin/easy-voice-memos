from pathlib import Path
from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.model.codec_config import CODEC_CONFIGS, CodecConfig, CodecPresets
from src.model.settings import AppSettings
from src.utils.ffmpeg_wrapper import FFmpegWrapper


class SettingsDialog(QDialog):
    """Settings and codec configuration dialog"""

    # Signals
    codec_config_changed = Signal(object)  # CodecConfig
    settings_changed = Signal(dict)  # settings dict

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        app_settings: Optional[AppSettings] = None,
    ):
        """Initialize settings dialog

        Args:
            parent: Parent widget
            app_settings: Application settings instance
        """
        super().__init__(parent)

        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(800)

        self._codec_config: Optional[CodecConfig] = None
        self._settings: dict = {}
        self._app_settings = app_settings  # Store reference to app settings

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup UI components"""
        layout = QVBoxLayout(self)

        # Tab widget
        tabs = QTabWidget()

        # Recording tab
        recording_tab = self._create_recording_tab()
        tabs.addTab(recording_tab, "Recording")

        # General tab
        general_tab = self._create_general_tab()
        tabs.addTab(general_tab, "General")

        # About tab
        about_tab = self._create_about_tab()
        tabs.addTab(about_tab, "About")

        layout.addWidget(tabs)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._on_save)
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _create_recording_tab(self) -> QWidget:
        """Create recording settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Preset section
        preset_group = QGroupBox("Quick Presets")
        preset_layout = QVBoxLayout()

        self._preset_combo = QComboBox()
        self._populate_presets()
        self._preset_combo.currentTextChanged.connect(self._on_preset_changed)
        preset_layout.addWidget(self._preset_combo)

        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)

        # Custom Presets Management
        custom_preset_group = QGroupBox("Custom Presets")
        custom_preset_layout = QHBoxLayout()

        self._save_preset_btn = QPushButton("Save Current as Preset...")
        self._save_preset_btn.clicked.connect(self._on_save_preset)
        custom_preset_layout.addWidget(self._save_preset_btn)

        self._delete_preset_btn = QPushButton("Delete Selected Preset")
        self._delete_preset_btn.clicked.connect(self._on_delete_preset)
        custom_preset_layout.addWidget(self._delete_preset_btn)

        custom_preset_layout.addStretch()
        custom_preset_group.setLayout(custom_preset_layout)
        layout.addWidget(custom_preset_group)

        # Advanced settings
        advanced_group = QGroupBox("Advanced Settings")
        advanced_layout = QVBoxLayout()

        # Codec selection
        codec_layout = QHBoxLayout()
        codec_layout.addWidget(QLabel("Codec:"))
        self._codec_combo = QComboBox()
        for codec_name in CODEC_CONFIGS.keys():
            self._codec_combo.addItem(codec_name.upper(), codec_name)
        self._codec_combo.currentTextChanged.connect(self._on_codec_changed)
        codec_layout.addWidget(self._codec_combo)
        codec_layout.addStretch()
        advanced_layout.addLayout(codec_layout)

        # Sample rate
        sample_layout = QHBoxLayout()
        sample_layout.addWidget(QLabel("Sample Rate:"))
        self._sample_rate_combo = QComboBox()
        sample_layout.addWidget(self._sample_rate_combo)
        sample_layout.addStretch()
        advanced_layout.addLayout(sample_layout)

        # Bit rate
        bitrate_layout = QHBoxLayout()
        self._bitrate_label = QLabel("Bit Rate:")
        bitrate_layout.addWidget(self._bitrate_label)
        self._bitrate_combo = QComboBox()
        bitrate_layout.addWidget(self._bitrate_combo)
        bitrate_layout.addStretch()
        advanced_layout.addLayout(bitrate_layout)

        # Channels
        channels_layout = QHBoxLayout()
        channels_layout.addWidget(QLabel("Channels:"))
        self._channels_group = QButtonGroup()
        self._mono_radio = QRadioButton("Mono")
        self._stereo_radio = QRadioButton("Stereo")
        self._channels_group.addButton(self._mono_radio, 1)
        self._channels_group.addButton(self._stereo_radio, 2)
        self._mono_radio.setChecked(True)
        channels_layout.addWidget(self._mono_radio)
        channels_layout.addWidget(self._stereo_radio)
        channels_layout.addStretch()
        advanced_layout.addLayout(channels_layout)

        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)

        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()

        self._auto_convert_check = QCheckBox("Auto-convert after recording")
        self._auto_convert_check.setChecked(True)
        options_layout.addWidget(self._auto_convert_check)

        self._keep_wav_check = QCheckBox("Keep original WAV file")
        options_layout.addWidget(self._keep_wav_check)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        layout.addStretch()

        # Initialize with first codec
        self._on_codec_changed(self._codec_combo.currentText())

        return widget

    def _create_general_tab(self) -> QWidget:
        """Create general settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Storage directory
        storage_group = QGroupBox("Storage")
        storage_layout = QVBoxLayout()

        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Memo Directory:"))

        self._storage_dir_edit = QLineEdit()
        dir_layout.addWidget(self._storage_dir_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse_storage)
        dir_layout.addWidget(browse_btn)

        storage_layout.addLayout(dir_layout)
        storage_group.setLayout(storage_layout)
        layout.addWidget(storage_group)

        # File naming
        naming_group = QGroupBox("File Naming")
        naming_layout = QVBoxLayout()

        prefix_layout = QHBoxLayout()
        prefix_layout.addWidget(QLabel("Default Prefix:"))
        self._prefix_edit = QLineEdit()
        self._prefix_edit.setText("memo")
        prefix_layout.addWidget(self._prefix_edit)
        prefix_layout.addStretch()
        naming_layout.addLayout(prefix_layout)

        naming_group.setLayout(naming_layout)
        layout.addWidget(naming_group)

        layout.addStretch()
        return widget

    def _create_about_tab(self) -> QWidget:
        """Create about tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # App info
        title = QLabel("Easy Voice Memos")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        version = QLabel("Version 1.0.0")
        layout.addWidget(version)

        layout.addSpacing(20)

        # FFmpeg info
        ffmpeg_label = QLabel("FFmpeg Information:")
        ffmpeg_label.setObjectName("titleLabel")
        layout.addWidget(ffmpeg_label)

        ffmpeg = FFmpegWrapper()
        version_text = ffmpeg.get_version()

        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setMaximumHeight(100)
        info_text.setPlainText(version_text)
        layout.addWidget(info_text)

        # Supported codecs
        codecs_label = QLabel("Supported Codecs:")
        codecs_label.setObjectName("titleLabel")
        layout.addWidget(codecs_label)

        codec_list = ", ".join(CODEC_CONFIGS.keys())
        codecs_text = QLabel(codec_list.upper())
        codecs_text.setWordWrap(True)
        layout.addWidget(codecs_text)

        layout.addStretch()
        return widget

    def _populate_presets(self) -> None:
        """Populate preset combo box with built-in and custom presets"""
        self._preset_combo.clear()

        # Get all presets (built-in + custom)
        if self._app_settings:
            all_presets = self._app_settings.get_all_presets()
        else:
            all_presets = CodecPresets.get_all_presets()

        for preset_name in all_presets.keys():
            self._preset_combo.addItem(preset_name)

    def _on_preset_changed(self, preset_name: str) -> None:
        """Handle preset change"""
        # Get preset from app settings if available, otherwise from built-in
        if self._app_settings:
            all_presets = self._app_settings.get_all_presets()
        else:
            all_presets = CodecPresets.get_all_presets()

        if preset_name in all_presets:
            config = all_presets[preset_name]
            self._load_codec_config(config)

    def _on_codec_changed(self, codec_text: str) -> None:
        """Handle codec change"""
        codec_name = codec_text.lower()

        if codec_name not in CODEC_CONFIGS:
            return

        codec_info = CODEC_CONFIGS[codec_name]

        # Update sample rates
        self._sample_rate_combo.clear()
        for rate in codec_info["sample_rates"]:
            self._sample_rate_combo.addItem(f"{rate} Hz", rate)

        # Update bit rates
        bit_rates = codec_info.get("bit_rates")
        if bit_rates:
            self._bitrate_combo.clear()
            self._bitrate_combo.setEnabled(True)
            self._bitrate_label.setEnabled(True)
            for rate in bit_rates:
                self._bitrate_combo.addItem(f"{rate // 1000} kbps", rate)
        else:
            # Lossless codec
            self._bitrate_combo.clear()
            self._bitrate_combo.setEnabled(False)
            self._bitrate_label.setEnabled(False)
            self._bitrate_combo.addItem("Lossless", None)

    def _on_browse_storage(self) -> None:
        """Browse for storage directory"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Storage Directory", self._storage_dir_edit.text()
        )
        if directory:
            self._storage_dir_edit.setText(directory)

    def _on_save_preset(self) -> None:
        """Save current configuration as a custom preset"""
        # Get preset name from user
        name, ok = QInputDialog.getText(
            self, "Save Preset", "Enter preset name:", text="My Custom Preset"
        )

        if ok and name:
            # Get current codec configuration
            codec_name = self._codec_combo.currentData()
            sample_rate = self._sample_rate_combo.currentData()
            bit_rate = self._bitrate_combo.currentData()
            channels = self._channels_group.checkedId()

            config = CodecConfig(
                codec_name=codec_name,
                sample_rate=sample_rate,
                bit_rate=bit_rate,
                channels=channels,
            )

            # Save to app settings if available
            if self._app_settings:
                success = self._app_settings.add_custom_preset(name, config)
                if not success:
                    QMessageBox.warning(
                        self,
                        "Cannot Save",
                        "Cannot overwrite built-in presets. Please choose a different name.",
                    )
                    return

                # Refresh preset list
                self._populate_presets()
                self._preset_combo.setCurrentText(name)

                QMessageBox.information(
                    self, "Preset Saved", f"Custom preset '{name}' has been saved!"
                )
            else:
                QMessageBox.warning(
                    self, "Error", "Cannot save preset: Settings not available"
                )

    def _on_delete_preset(self) -> None:
        """Delete the currently selected preset if it's custom"""

        current_preset = self._preset_combo.currentText()

        # Check if it's a built-in preset
        if current_preset in CodecPresets.get_all_presets():
            QMessageBox.warning(
                self,
                "Cannot Delete",
                "Cannot delete built-in presets. Only custom presets can be deleted.",
            )
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Preset",
            f"Are you sure you want to delete the preset '{current_preset}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Delete from app settings if available
            if self._app_settings:
                success = self._app_settings.remove_custom_preset(current_preset)
                if success:
                    # Refresh preset list
                    self._populate_presets()

                    QMessageBox.information(
                        self,
                        "Preset Deleted",
                        f"Custom preset '{current_preset}' has been deleted!",
                    )
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete preset.")
            else:
                QMessageBox.warning(
                    self, "Error", "Cannot delete preset: Settings not available"
                )

    def _on_save(self) -> None:
        """Handle save button"""
        # Build codec config
        codec_name = self._codec_combo.currentData()
        sample_rate = self._sample_rate_combo.currentData()
        bit_rate = self._bitrate_combo.currentData()
        channels = self._channels_group.checkedId()

        self._codec_config = CodecConfig(
            codec_name=codec_name,
            sample_rate=sample_rate,
            bit_rate=bit_rate,
            channels=channels,
        )

        # Build settings dict
        self._settings = {
            "storage_directory": self._storage_dir_edit.text(),
            "default_file_prefix": self._prefix_edit.text(),
            "auto_convert_after_recording": self._auto_convert_check.isChecked(),
            "keep_original_wav": self._keep_wav_check.isChecked(),
            "last_preset": self._preset_combo.currentText(),
        }

        # Emit signals
        self.codec_config_changed.emit(self._codec_config)
        self.settings_changed.emit(self._settings)

        self.accept()

    def _load_codec_config(self, config: CodecConfig) -> None:
        """Load codec configuration into UI"""
        # Set codec
        index = self._codec_combo.findData(config.codec_name)
        if index >= 0:
            self._codec_combo.setCurrentIndex(index)

        # Set sample rate
        index = self._sample_rate_combo.findData(config.sample_rate)
        if index >= 0:
            self._sample_rate_combo.setCurrentIndex(index)

        # Set bit rate
        if config.bit_rate:
            index = self._bitrate_combo.findData(config.bit_rate)
            if index >= 0:
                self._bitrate_combo.setCurrentIndex(index)

        # Set channels
        if config.channels == 1:
            self._mono_radio.setChecked(True)
        else:
            self._stereo_radio.setChecked(True)

    def set_codec_config(self, config: CodecConfig) -> None:
        """Set initial codec configuration"""
        self._codec_config = config
        self._load_codec_config(config)

    def set_settings(self, settings: dict) -> None:
        """Set initial settings"""
        self._settings = settings

        if "storage_directory" in settings:
            self._storage_dir_edit.setText(settings["storage_directory"])

        if "default_file_prefix" in settings:
            self._prefix_edit.setText(settings["default_file_prefix"])

        if "auto_convert_after_recording" in settings:
            self._auto_convert_check.setChecked(
                settings["auto_convert_after_recording"]
            )

        if "keep_original_wav" in settings:
            self._keep_wav_check.setChecked(settings["keep_original_wav"])

        if "last_preset" in settings:
            index = self._preset_combo.findText(settings["last_preset"])
            if index >= 0:
                self._preset_combo.setCurrentIndex(index)
