from pathlib import Path
from typing import Optional

import numpy as np
from PySide6.QtCore import QObject

from src.model.audio_player import AudioPlayer
from src.model.memo_manager import VoiceMemo
from src.model.spectrogram_data import SpectrogramData
from src.model.waveform_data import WaveformData
from src.view.playback_widget import PlaybackWidget
from src.view.spectrogram_widget import SpectrogramWidget
from src.view.waveform_widget import WaveformWidget


class PlaybackController(QObject):
    """Controller for playback workflow"""

    def __init__(
        self,
        audio_player: AudioPlayer,
        playback_widget: PlaybackWidget,
        waveform_widget: WaveformWidget,
        spectrogram_widget: SpectrogramWidget,
        parent: Optional[QObject] = None,
    ):
        """Initialize playback controller

        Args:
            audio_player: Audio player model
            playback_widget: Playback widget view
            waveform_widget: Waveform widget view
            spectrogram_widget: Spectrogram widget view
            parent: Parent QObject
        """
        super().__init__(parent)

        self._player = audio_player
        self._playback_widget = playback_widget
        self._waveform_widget = waveform_widget
        self._spectrogram = spectrogram_widget

        # Current state
        self._current_memo: Optional[VoiceMemo] = None
        self._waveform_data: Optional[WaveformData] = None
        self._spectrogram_data: Optional[SpectrogramData] = None

        self._connect_signals()

    def _connect_signals(self) -> None:
        """Connect model and view signals"""
        # Playback widget signals
        self._playback_widget.play_clicked.connect(self.play)
        self._playback_widget.pause_clicked.connect(self.pause)
        self._playback_widget.stop_clicked.connect(self.stop)
        self._playback_widget.seek_requested.connect(self.seek)
        self._playback_widget.volume_changed.connect(self._player.set_volume)

        # Waveform widget signals
        self._waveform_widget.seek_requested.connect(self._on_waveform_seek)

        # Spectrogram widget signals
        self._spectrogram.seek_requested.connect(self._on_spectrogram_seek)

        # Player signals
        self._player.playback_started.connect(self._on_playback_started)
        self._player.playback_paused.connect(self._on_playback_paused)
        self._player.playback_stopped.connect(self._on_playback_stopped)
        self._player.playback_finished.connect(self._on_playback_finished)
        self._player.position_changed.connect(self._on_position_changed)
        self._player.duration_changed.connect(self._on_duration_changed)
        self._player.error_occurred.connect(self._on_error)

    def load_memo(self, memo: VoiceMemo) -> bool:
        """Load a memo for playback

        Args:
            memo: VoiceMemo to load

        Returns:
            True if loaded successfully
        """
        file_path = Path(memo.file_path)

        # Stop current playback
        if self._player.is_playing():
            self._player.stop()

        # Load file
        if not self._player.load_file(file_path):
            return False

        self._current_memo = memo

        # Load waveform
        self._load_waveform(file_path)

        # Load spectrogram
        self._load_spectrogram(file_path)

        # Enable playback controls
        self._playback_widget.set_enabled(True)

        return True

    def play(self) -> None:
        """Start or resume playback"""
        if self._current_memo:
            self._player.play()

    def pause(self) -> None:
        """Pause playback"""
        if self._player.is_playing():
            self._player.pause()

    def stop(self) -> None:
        """Stop playback"""
        if self._player.is_playing() or self._player.is_paused():
            self._player.stop()

    def seek(self, position_ms: int) -> None:
        """Seek to position

        Args:
            position_ms: Position in milliseconds
        """
        self._player.seek(position_ms)

    def unload(self) -> None:
        """Unload current memo"""
        self.stop()
        self._current_memo = None
        self._waveform_widget.clear()
        self._spectrogram.clear()
        self._playback_widget.reset()

    def _load_waveform(self, file_path: Path) -> None:
        """Load waveform for visualization

        Args:
            file_path: Audio file path
        """
        try:
            self._waveform_data = WaveformData(file_path)
            waveform = self._waveform_data.extract_waveform(resolution=1000)

            if waveform is not None:
                # Normalize waveform
                normalized = self._waveform_data.normalize_waveform()
                self._waveform_widget.set_waveform_data(normalized)
            else:
                self._waveform_widget.set_waveform_data(None)

        except Exception as e:
            print(f"Failed to load waveform: {e}")
            self._waveform_widget.set_waveform_data(None)

    def _load_spectrogram(self, file_path: Path) -> None:
        """Load spectrogram for visualization

        Args:
            file_path: Audio file path
        """
        try:
            self._spectrogram_data = SpectrogramData(file_path)
            spectrogram, freq_bins = self._spectrogram_data.extract_spectrogram(
                n_fft=2048, hop_length=512, freq_min=80.0, freq_max=8000.0
            )

            if spectrogram is not None and len(spectrogram) > 0:
                self._spectrogram.set_spectrogram_data(spectrogram, freq_bins)
            else:
                self._spectrogram.clear()

        except Exception as e:
            print(f"Failed to load spectrogram: {e}")
            import traceback

            traceback.print_exc()
            self._spectrogram.clear()

    def _on_waveform_seek(self, position: float) -> None:
        """Handle seek from waveform click

        Args:
            position: Position from 0.0 to 1.0
        """
        if self._current_memo:
            duration = self._player.get_duration()
            position_ms = int(position * duration)
            self.seek(position_ms)

    def _on_spectrogram_seek(self, position: float) -> None:
        """Handle seek from spectrogram click

        Args:
            position: Position from 0.0 to 1.0
        """
        if self._current_memo:
            duration = self._player.get_duration()
            position_ms = int(position * duration)
            self.seek(position_ms)

    # Signal handlers
    def _on_playback_started(self) -> None:
        """Handle playback started"""
        self._playback_widget.set_playback_state(True)

    def _on_playback_paused(self) -> None:
        """Handle playback paused"""
        self._playback_widget.set_playback_state(False)

    def _on_playback_stopped(self) -> None:
        """Handle playback stopped"""
        self._playback_widget.set_playback_state(False)
        self._waveform_widget.set_playback_position(0.0)
        self._spectrogram.set_playback_position(0.0)

    def _on_playback_finished(self) -> None:
        """Handle playback finished"""
        self._playback_widget.set_playback_state(False)
        self._waveform_widget.set_playback_position(0.0)
        self._spectrogram.set_playback_position(0.0)
        # Reset to beginning
        self._player.seek(0)

    def _on_position_changed(self, position_ms: int) -> None:
        """Handle position change

        Args:
            position_ms: Position in milliseconds
        """
        self._playback_widget.update_position(position_ms)

        # Update waveform and spectrogram position
        duration = self._player.get_duration()
        if duration > 0:
            position_ratio = position_ms / duration
            self._waveform_widget.set_playback_position(position_ratio)
            self._spectrogram.set_playback_position(position_ratio)

    def _on_duration_changed(self, duration_ms: int) -> None:
        """Handle duration change

        Args:
            duration_ms: Duration in milliseconds
        """
        self._playback_widget.update_duration(duration_ms)

    def _on_error(self, error: str) -> None:
        """Handle playback error

        Args:
            error: Error message
        """
        print(f"Playback error: {error}")
        self._playback_widget.set_playback_state(False)

    def get_current_memo(self) -> Optional[VoiceMemo]:
        """Get currently loaded memo

        Returns:
            Current VoiceMemo or None
        """
        return self._current_memo
