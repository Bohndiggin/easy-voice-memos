from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QMessageBox

from src.controller.memo_controller import MemoController
from src.controller.playback_controller import PlaybackController
from src.controller.recording_controller import RecordingController
from src.model.audio_player import AudioPlayer
from src.model.audio_recorder import AudioRecorder
from src.model.codec_config import CodecPresets
from src.model.format_converter import FormatConverter
from src.model.memo_manager import MemoManager
from src.model.settings import AppSettings
from src.view.main_window import MainWindow
from src.view.settings_dialog import SettingsDialog


class MainController(QObject):
    """Main application controller - coordinates all components"""

    def __init__(self, main_window: MainWindow, parent: Optional[QObject] = None):
        """Initialize main controller

        Args:
            main_window: Main window view
            parent: Parent QObject
        """
        super().__init__(parent)

        self._window = main_window
        self._settings = AppSettings()

        # Initialize models
        self._audio_recorder = AudioRecorder()
        self._audio_player = AudioPlayer()
        self._format_converter = FormatConverter()
        self._memo_manager = MemoManager(self._settings.get_storage_directory())

        # Initialize sub-controllers
        self._recording_controller: Optional[RecordingController] = None
        self._playback_controller: Optional[PlaybackController] = None
        self._memo_controller: Optional[MemoController] = None

        # Apply settings
        self._apply_initial_settings()

    def initialize(self) -> None:
        """Initialize controllers and connect signals"""
        # Pass settings to recording panel for custom presets
        self._window.recording_panel._app_settings = self._settings
        self._window.recording_panel._preset_combo.clear()
        self._window.recording_panel._populate_presets()

        # Create sub-controllers
        self._recording_controller = RecordingController(
            audio_recorder=self._audio_recorder,
            recording_panel=self._window.recording_panel,
            waveform_widget=self._window.waveform_widget,
            spectrogram_widget=self._window.spectrogram_widget,
            format_converter=self._format_converter,
            storage_dir=self._settings.get_storage_directory(),
        )

        self._playback_controller = PlaybackController(
            audio_player=self._audio_player,
            playback_widget=self._window.playback_widget,
            waveform_widget=self._window.waveform_widget,
            spectrogram_widget=self._window.spectrogram_widget,
        )

        self._memo_controller = MemoController(
            memo_manager=self._memo_manager,
            memo_list_widget=self._window.memo_list_widget,
            format_converter=self._format_converter,
        )

        # Connect signals
        self._connect_signals()

        # Update initial status
        self._update_status()

    def _connect_signals(self) -> None:
        """Connect all signals between components"""
        # Window signals
        self._window.settings_requested.connect(self._show_settings_dialog)
        self._window.about_requested.connect(self._show_about_dialog)
        self._window.quit_requested.connect(self._on_quit)

        # Recording panel signals
        self._window.recording_panel.settings_clicked.connect(
            self._show_settings_dialog
        )
        self._window.recording_panel.preset_changed.connect(self._on_preset_changed)

        # Memo controller signals
        self._memo_controller.memo_selected.connect(self._on_memo_selected)
        self._memo_controller.memo_added.connect(self._on_memo_added)
        self._memo_controller.storage_updated.connect(self._on_storage_updated)

        # Recording controller - detect when recording stops
        self._audio_recorder.recording_stopped.connect(self._on_recording_stopped)

    def _apply_initial_settings(self) -> None:
        """Apply initial settings from config"""
        # Load codec config
        codec_config = self._settings.get_codec_config()

        # Apply to recording controller (will be set when initialized)
        # For now, store it
        self._current_codec_config = codec_config

        # Set last used preset
        last_preset = self._settings.get("last_preset", "Voice - Standard")
        # Will be applied when recording panel is ready

    def _on_preset_changed(self, preset_name: str) -> None:
        """Handle preset change

        Args:
            preset_name: Selected preset name
        """
        # Get all presets (built-in + custom)
        presets = self._settings.get_all_presets()
        if preset_name in presets:
            codec_config = presets[preset_name]
            self._current_codec_config = codec_config

            if self._recording_controller:
                self._recording_controller.set_codec_config(codec_config)

            # Save to settings
            self._settings.set_codec_config(codec_config)
            self._settings.set("last_preset", preset_name)
            self._settings.save()

    def _on_memo_selected(self, memo) -> None:
        """Handle memo selection

        Args:
            memo: Selected VoiceMemo
        """
        # Load memo for playback
        if self._playback_controller:
            self._playback_controller.load_memo(memo)
            self._window.set_status_message(f"Loaded: {memo.filename}")

    def _on_memo_added(self, memo) -> None:
        """Handle memo added

        Args:
            memo: Added VoiceMemo
        """
        self._window.set_status_message(f"Added: {memo.filename}")

    def _on_storage_updated(self, num_memos: int, total_size: int) -> None:
        """Handle storage info update

        Args:
            num_memos: Number of memos
            total_size: Total size in bytes
        """
        self._window.update_storage_info(num_memos, total_size)

    def _on_recording_stopped(self, file_path: str) -> None:
        """Handle recording stopped

        Args:
            file_path: Path to recorded file
        """
        # Refresh memo list to include new recording
        # Wait a bit for conversion if needed
        QTimer.singleShot(500, lambda: self._memo_controller.refresh_memo_list())

    def _show_settings_dialog(self) -> None:
        """Show settings dialog"""
        dialog = SettingsDialog(self._window, self._settings)

        # Load current settings
        dialog.set_codec_config(self._current_codec_config)
        dialog.set_settings(self._settings.get_all())

        # Connect signals
        dialog.codec_config_changed.connect(self._on_codec_config_changed)
        dialog.settings_changed.connect(self._on_settings_changed)

        dialog.exec()

        # Refresh recording panel presets after dialog closes
        self._window.recording_panel._app_settings = self._settings
        self._window.recording_panel._preset_combo.clear()
        self._window.recording_panel._populate_presets()

    def _on_codec_config_changed(self, codec_config) -> None:
        """Handle codec config change from settings

        Args:
            codec_config: New CodecConfig
        """
        self._current_codec_config = codec_config

        if self._recording_controller:
            self._recording_controller.set_codec_config(codec_config)

        # Save to settings
        self._settings.set_codec_config(codec_config)
        self._settings.save()

    def _on_settings_changed(self, settings: dict) -> None:
        """Handle settings change

        Args:
            settings: Settings dictionary
        """
        # Apply settings
        for key, value in settings.items():
            self._settings.set(key, value)

        # Update storage directory if changed
        if "storage_directory" in settings:
            new_dir = Path(settings["storage_directory"])
            self._memo_manager = MemoManager(new_dir)

            # Reconnect memo controller with new manager
            if self._memo_controller:
                self._memo_controller._manager = self._memo_manager
                self._memo_controller.refresh_memo_list()

            if self._recording_controller:
                self._recording_controller._storage_dir = new_dir

        # Update recording options
        if "auto_convert_after_recording" in settings and self._recording_controller:
            self._recording_controller.set_auto_convert(
                settings["auto_convert_after_recording"]
            )

        if "keep_original_wav" in settings and self._recording_controller:
            self._recording_controller.set_keep_wav(settings["keep_original_wav"])

        # Save settings
        self._settings.save()

    def _show_about_dialog(self) -> None:
        """Show about dialog"""
        QMessageBox.about(
            self._window,
            "About Easy Voice Memos",
            "<h3>Easy Voice Memos</h3>"
            "<p>Version 1.0.0</p>"
            "<p>A simple voice memo application with extensive codec support.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Multiple codec support (MP3, AAC, Opus, FLAC, etc.)</li>"
            "<li>Configurable quality settings</li>"
            "<li>Waveform visualization</li>"
            "<li>Format conversion</li>"
            "</ul>"
            "<p>Powered by FFmpeg and PySide6</p>",
        )

    def _on_quit(self) -> None:
        """Handle quit request"""
        # Stop any active recording or playback
        if self._audio_recorder.is_active():
            self._audio_recorder.stop_recording()

        if self._audio_player.is_playing():
            self._audio_player.stop()

        # Unload playback controller to stop any background threads
        if self._playback_controller:
            self._playback_controller.unload()

        # Save settings
        self._settings.save()

        # Close window
        self._window.close()

    def _update_status(self) -> None:
        """Update status bar"""
        num_memos = self._memo_manager.get_memo_count()
        total_size = self._memo_manager.get_total_storage()
        self._window.update_storage_info(num_memos, total_size)

    def shutdown(self) -> None:
        """Clean shutdown"""
        self._on_quit()
