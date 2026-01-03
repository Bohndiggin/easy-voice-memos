from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


class AudioPlayer(QObject):
    """Audio player using PySide6 QMediaPlayer

    Plays back audio files in various formats.
    """

    # Signals
    playback_started = Signal()
    playback_paused = Signal()
    playback_stopped = Signal()
    playback_finished = Signal()
    position_changed = Signal(int)  # Position in milliseconds
    duration_changed = Signal(int)  # Duration in milliseconds
    error_occurred = Signal(str)

    def __init__(self, parent: Optional[QObject] = None):
        """Initialize audio player

        Args:
            parent: Parent QObject
        """
        super().__init__(parent)

        # Audio output
        self._audio_output = QAudioOutput()

        # Media player
        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._audio_output)

        # Connect signals
        self._player.playbackStateChanged.connect(self._on_state_changed)
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.errorOccurred.connect(self._on_error)

        # Track current file
        self._current_file: Optional[Path] = None
        self._duration = 0

    def load_file(self, file_path: Path) -> bool:
        """Load an audio file for playback

        Args:
            file_path: Path to audio file

        Returns:
            True if file loaded successfully
        """
        try:
            if not file_path.exists():
                self.error_occurred.emit(f"File not found: {file_path}")
                return False

            self._current_file = file_path
            source_url = QUrl.fromLocalFile(str(file_path.absolute()))
            self._player.setSource(source_url)

            return True

        except Exception as e:
            self.error_occurred.emit(f"Failed to load file: {e}")
            return False

    def play(self) -> bool:
        """Start or resume playback

        Returns:
            True if playback started
        """
        try:
            self._player.play()
            return True
        except Exception as e:
            self.error_occurred.emit(f"Failed to play: {e}")
            return False

    def pause(self) -> bool:
        """Pause playback

        Returns:
            True if paused successfully
        """
        try:
            self._player.pause()
            return True
        except Exception as e:
            self.error_occurred.emit(f"Failed to pause: {e}")
            return False

    def stop(self) -> bool:
        """Stop playback and reset position

        Returns:
            True if stopped successfully
        """
        try:
            self._player.stop()
            return True
        except Exception as e:
            self.error_occurred.emit(f"Failed to stop: {e}")
            return False

    def seek(self, position_ms: int) -> bool:
        """Seek to a specific position

        Args:
            position_ms: Position in milliseconds

        Returns:
            True if seek successful
        """
        try:
            self._player.setPosition(position_ms)
            return True
        except Exception as e:
            self.error_occurred.emit(f"Failed to seek: {e}")
            return False

    def set_volume(self, level: float) -> None:
        """Set playback volume

        Args:
            level: Volume level from 0.0 (mute) to 1.0 (maximum)
        """
        level = max(0.0, min(1.0, level))
        self._audio_output.setVolume(level)

    def get_volume(self) -> float:
        """Get current volume level

        Returns:
            Volume level from 0.0 to 1.0
        """
        return self._audio_output.volume()

    def get_duration(self) -> int:
        """Get total duration of current file

        Returns:
            Duration in milliseconds
        """
        return self._duration

    def get_position(self) -> int:
        """Get current playback position

        Returns:
            Position in milliseconds
        """
        return self._player.position()

    def is_playing(self) -> bool:
        """Check if currently playing

        Returns:
            True if playing
        """
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def is_paused(self) -> bool:
        """Check if paused

        Returns:
            True if paused
        """
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PausedState

    def is_stopped(self) -> bool:
        """Check if stopped

        Returns:
            True if stopped
        """
        return self._player.playbackState() == QMediaPlayer.PlaybackState.StoppedState

    def get_current_file(self) -> Optional[Path]:
        """Get currently loaded file

        Returns:
            Path to current file or None
        """
        return self._current_file

    def get_playback_rate(self) -> float:
        """Get playback rate

        Returns:
            Playback rate (1.0 = normal speed)
        """
        return self._player.playbackRate()

    def set_playback_rate(self, rate: float) -> None:
        """Set playback rate

        Args:
            rate: Playback rate (0.5 = half speed, 2.0 = double speed)
        """
        self._player.setPlaybackRate(rate)

    # Private slots
    def _on_state_changed(self, state):
        """Handle playback state changes"""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.playback_started.emit()
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.playback_paused.emit()
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            # Check if we reached the end
            if self._player.position() >= self._duration and self._duration > 0:
                self.playback_finished.emit()
            else:
                self.playback_stopped.emit()

    def _on_position_changed(self, position):
        """Handle position changes"""
        self.position_changed.emit(position)

    def _on_duration_changed(self, duration):
        """Handle duration changes"""
        self._duration = duration
        self.duration_changed.emit(duration)

    def _on_error(self, error, error_string):
        """Handle errors"""
        self.error_occurred.emit(f"Playback error: {error_string}")
