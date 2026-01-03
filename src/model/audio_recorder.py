from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import (
    QAudioInput,
    QMediaCaptureSession,
    QMediaFormat,
    QMediaRecorder,
)

from src.model.audio_level_monitor import AudioLevelMonitor
from src.model.codec_config import CodecConfig


class AudioRecorder(QObject):
    """Audio recorder using PySide6 QMediaRecorder

    Records audio to WAV format initially. Can be converted to other
    formats after recording using FFmpeg.
    """

    # Signals
    recording_started = Signal()
    recording_stopped = Signal(str)  # Emits file path
    recording_paused = Signal()
    recording_resumed = Signal()
    audio_level_changed = Signal(float)  # 0.0 to 1.0
    duration_changed = Signal(int)  # Duration in milliseconds
    error_occurred = Signal(str)

    def __init__(self, parent: Optional[QObject] = None):
        """Initialize audio recorder

        Args:
            parent: Parent QObject
        """
        super().__init__(parent)

        # Audio input
        self._audio_input = QAudioInput()

        # Capture session
        self._capture_session = QMediaCaptureSession()
        self._capture_session.setAudioInput(self._audio_input)

        # Media recorder
        self._recorder = QMediaRecorder()
        self._capture_session.setRecorder(self._recorder)

        # Set default format to WAV (uncompressed)
        media_format = QMediaFormat()
        media_format.setFileFormat(QMediaFormat.FileFormat.Wave)
        media_format.setAudioCodec(QMediaFormat.AudioCodec.Wave)
        self._recorder.setMediaFormat(media_format)

        # Set quality to highest
        self._recorder.setQuality(QMediaRecorder.Quality.VeryHighQuality)

        # Connect signals
        self._recorder.recorderStateChanged.connect(self._on_state_changed)
        self._recorder.durationChanged.connect(self._on_duration_changed)
        self._recorder.errorOccurred.connect(self._on_error)

        # Track current file
        self._current_file: Optional[Path] = None
        self._is_paused = False

        # Audio level monitoring (real-time buffer analysis)
        self._level_monitor = AudioLevelMonitor()
        self._level_monitor.level_changed.connect(self._on_level_changed)
        self._current_audio_level = 0.0

    def start_recording(self, output_path: Path) -> bool:
        """Start recording audio

        Args:
            output_path: Path where recording will be saved

        Returns:
            True if recording started successfully
        """
        try:
            self._current_file = output_path
            self._is_paused = False

            # Set output location
            output_url = QUrl.fromLocalFile(str(output_path.absolute()))
            self._recorder.setOutputLocation(output_url)

            # Start recording
            self._recorder.record()

            # Start level monitoring with the file path
            self._level_monitor.start(output_path)

            return True

        except Exception as e:
            self.error_occurred.emit(f"Failed to start recording: {e}")
            return False

    def stop_recording(self) -> Optional[Path]:
        """Stop recording and return file path

        Returns:
            Path to recorded file or None if no recording
        """
        if self._recorder.recorderState() != QMediaRecorder.RecorderState.StoppedState:
            self._recorder.stop()

        # Stop level monitoring
        self._level_monitor.stop()
        self._current_audio_level = 0.0

        return self._current_file

    def pause_recording(self) -> bool:
        """Pause current recording

        Returns:
            True if paused successfully
        """
        if (
            self._recorder.recorderState()
            == QMediaRecorder.RecorderState.RecordingState
        ):
            self._recorder.pause()
            self._is_paused = True
            return True
        return False

    def resume_recording(self) -> bool:
        """Resume paused recording

        Returns:
            True if resumed successfully
        """
        if self._recorder.recorderState() == QMediaRecorder.RecorderState.PausedState:
            self._recorder.record()
            self._is_paused = False
            return True
        return False

    def get_recording_duration(self) -> float:
        """Get current recording duration in seconds

        Returns:
            Duration in seconds
        """
        return self._recorder.duration() / 1000.0

    def get_audio_level(self) -> float:
        """Get current audio input level

        Returns:
            Audio level from 0.0 (silence) to 1.0 (maximum)
        """
        return self._current_audio_level

    def is_recording(self) -> bool:
        """Check if currently recording

        Returns:
            True if recording (not paused)
        """
        return (
            self._recorder.recorderState()
            == QMediaRecorder.RecorderState.RecordingState
        )

    def is_paused(self) -> bool:
        """Check if recording is paused

        Returns:
            True if paused
        """
        return self._is_paused

    def is_active(self) -> bool:
        """Check if recorder is active (recording or paused)

        Returns:
            True if active
        """
        state = self._recorder.recorderState()
        return state in (
            QMediaRecorder.RecorderState.RecordingState,
            QMediaRecorder.RecorderState.PausedState,
        )

    def set_audio_input_device(self, device) -> None:
        """Set audio input device

        Args:
            device: QAudioDevice object
        """
        self._audio_input.setDevice(device)
        # Note: Level monitor no longer needs device - it reads from WAV file

    def get_available_audio_codecs(self):
        """Get list of available audio codecs

        Returns:
            List of QMediaFormat.AudioCodec values
        """
        return QMediaFormat().supportedAudioCodecs(QMediaFormat.Encode)

    # Private slots
    def _on_state_changed(self, state):
        """Handle recorder state changes"""
        if state == QMediaRecorder.RecorderState.RecordingState:
            if not self._is_paused:
                self.recording_started.emit()
            else:
                self.recording_resumed.emit()
        elif state == QMediaRecorder.RecorderState.PausedState:
            self.recording_paused.emit()
        elif state == QMediaRecorder.RecorderState.StoppedState:
            if self._current_file:
                self.recording_stopped.emit(str(self._current_file))

    def _on_duration_changed(self, duration):
        """Handle duration changes"""
        self.duration_changed.emit(duration)

    def _on_error(self, error, error_string):
        """Handle errors"""
        self.error_occurred.emit(f"Recording error: {error_string}")

    def _on_level_changed(self, level: float):
        """Handle audio level change from monitor

        Args:
            level: Audio level from 0.0 to 1.0
        """
        self._current_audio_level = level
        self.audio_level_changed.emit(level)
