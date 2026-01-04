from pathlib import Path
from typing import Optional

import numpy as np
from PySide6.QtCore import QObject

from src.model.audio_player import AudioPlayer
from src.model.memo_manager import VoiceMemo
from src.model.spectrogram_data import SpectrogramData, SpectrogramWorker
from src.model.viewport_state import ViewportState
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
        self._spectrogram_worker: Optional[SpectrogramWorker] = None

        # Create shared viewport state for synchronized zoom/pan
        self._viewport_state = ViewportState(self)

        # Pass viewport state to visualization widgets
        self._waveform_widget.set_viewport_state(self._viewport_state)
        self._spectrogram.set_viewport_state(self._viewport_state)

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

        # Viewport signals
        self._viewport_state.zoom_level_changed.connect(self._on_zoom_level_changed)

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

        # Cancel any existing spectrogram worker
        if self._spectrogram_worker and self._spectrogram_worker.isRunning():
            self._spectrogram_worker.cancel()
            self._spectrogram_worker.wait()  # Wait for thread to finish

        # Load file
        if not self._player.load_file(file_path):
            return False

        self._current_memo = memo

        # Reset viewport to fit-all for new file
        self._viewport_state.reset()

        # Load waveform and spectrogram with resolutions matching the initial zoom level (1.0)
        initial_resolution = self._viewport_state.get_recommended_resolution()
        initial_hop_length = self._viewport_state.get_recommended_hop_length()

        # Load waveform (fast, keep synchronous)
        self._load_waveform(file_path, resolution=initial_resolution)

        # Load spectrogram asynchronously
        self._load_spectrogram_async(file_path, hop_length=initial_hop_length)

        # Enable playback controls immediately
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
        # Cancel spectrogram worker if running
        if self._spectrogram_worker and self._spectrogram_worker.isRunning():
            self._spectrogram_worker.cancel()
            self._spectrogram_worker.wait()  # Wait for thread to finish
            self._spectrogram_worker = None

        self.stop()
        self._current_memo = None
        self._waveform_widget.clear()
        self._spectrogram.clear()
        self._playback_widget.reset()

    def _load_waveform(self, file_path: Path, resolution: int = 1024) -> None:
        """Load waveform for visualization

        Args:
            file_path: Audio file path
            resolution: Number of waveform samples to extract
        """
        try:
            self._waveform_data = WaveformData(file_path)
            waveform = self._waveform_data.extract_waveform(resolution=resolution)

            if waveform is not None:
                # Normalize waveform
                normalized = self._waveform_data.normalize_waveform()
                if normalized is not None:
                    self._waveform_widget.set_waveform_data(normalized)
                else:
                    self._waveform_widget.set_waveform_data(None)
            else:
                self._waveform_widget.set_waveform_data(None)

        except Exception as e:
            print(f"Failed to load waveform: {e}")
            self._waveform_widget.set_waveform_data(None)

    def _load_spectrogram_async(self, file_path: Path, hop_length: int = 1024) -> None:
        """Load spectrogram in background thread

        Args:
            file_path: Audio file path
            hop_length: STFT hop length (smaller = better temporal resolution)
        """
        # Cancel any existing worker first
        if self._spectrogram_worker and self._spectrogram_worker.isRunning():
            self._spectrogram_worker.cancel()
            self._spectrogram_worker.wait()

        # Show loading state
        self._spectrogram.set_loading_state(True)

        # Create and start worker thread
        self._spectrogram_worker = SpectrogramWorker(
            file_path,
            n_fft=1024,  # Keep FFT size constant
            hop_length=hop_length,  # Vary hop length based on zoom
            freq_min=80.0,
            freq_max=8000.0,
            parent=self  # Set parent for proper Qt lifecycle management
        )

        # Connect signals
        self._spectrogram_worker.progress_updated.connect(
            self._on_spectrogram_progress
        )
        self._spectrogram_worker.computation_finished.connect(
            self._on_spectrogram_loaded
        )
        self._spectrogram_worker.computation_failed.connect(
            self._on_spectrogram_failed
        )

        # Start background computation
        self._spectrogram_worker.start()

    def _on_spectrogram_progress(self, message: str) -> None:
        """Handle spectrogram loading progress

        Args:
            message: Progress message
        """
        # Could show in status bar or on widget
        print(f"Spectrogram: {message}")

    def _on_spectrogram_loaded(
        self, spectrogram: np.ndarray, freq_bins: np.ndarray
    ) -> None:
        """Handle spectrogram computation completion

        Args:
            spectrogram: Spectrogram data
            freq_bins: Frequency bins
        """
        if spectrogram is not None and len(spectrogram) > 0:
            self._spectrogram.set_spectrogram_data(spectrogram, freq_bins)
        self._spectrogram.set_loading_state(False)
        self._spectrogram_worker = None

    def _on_spectrogram_failed(self, error: str) -> None:
        """Handle spectrogram computation failure

        Args:
            error: Error message
        """
        print(f"Spectrogram failed: {error}")
        self._spectrogram.clear()
        self._spectrogram.set_loading_state(False)
        self._spectrogram_worker = None

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

    def _on_zoom_level_changed(self, zoom_level: float) -> None:
        """Handle zoom level change - re-extract waveform and spectrogram at higher resolution

        Args:
            zoom_level: New zoom level
        """
        if not self._current_memo or not self._waveform_data:
            return

        # Get recommended parameters for current zoom level
        new_resolution = self._viewport_state.get_recommended_resolution()
        new_hop_length = self._viewport_state.get_recommended_hop_length()

        # Re-extract both visualizations at new resolution
        file_path = Path(self._current_memo.file_path)
        print(f"Zoom level changed to {zoom_level:.1f}x - re-extracting at higher resolution")
        print(f"  Waveform: {new_resolution} samples, Spectrogram: hop_length={new_hop_length}")

        self._load_waveform(file_path, resolution=new_resolution)
        self._load_spectrogram_async(file_path, hop_length=new_hop_length)

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
