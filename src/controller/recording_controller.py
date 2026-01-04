from collections import deque
from pathlib import Path
from typing import Optional

import numpy as np
from PySide6.QtCore import QObject, QTimer

from src.model.audio_recorder import AudioRecorder
from src.model.codec_config import CodecConfig
from src.model.format_converter import FormatConverter
from src.utils.audio_utils import AudioUtils
from src.view.recording_panel import RecordingPanel
from src.view.spectrogram_widget import SpectrogramWidget
from src.view.waveform_widget import WaveformWidget


class RecordingController(QObject):
    """Controller for recording workflow"""

    def __init__(
        self,
        audio_recorder: AudioRecorder,
        recording_panel: RecordingPanel,
        waveform_widget: WaveformWidget,
        spectrogram_widget: SpectrogramWidget,
        format_converter: FormatConverter,
        storage_dir: Path,
        parent: Optional[QObject] = None,
    ):
        """Initialize recording controller

        Args:
            audio_recorder: Audio recorder model
            recording_panel: Recording panel view
            waveform_widget: Waveform widget view
            spectrogram_widget: Spectrogram widget view
            format_converter: Format converter model
            storage_dir: Directory to save recordings
            parent: Parent QObject
        """
        super().__init__(parent)

        self._recorder = audio_recorder
        self._panel = recording_panel
        self._waveform = waveform_widget
        self._spectrogram = spectrogram_widget
        self._converter = format_converter
        self._storage_dir = Path(storage_dir)

        # Current recording state
        self._current_file: Optional[Path] = None
        self._codec_config: Optional[CodecConfig] = None
        self._auto_convert = True
        self._keep_wav = False

        # Live waveform buffer (store last 1000 samples for visualization)
        self._waveform_buffer = deque(maxlen=1000)

        # Live spectrogram buffer (store recent STFT slices)
        self._spectrogram_buffer = []
        self._max_spectrogram_slices = 200  # ~10 seconds at 50ms updates
        self._frequency_bins = None  # Frequency bins for spectrogram

        # Timer for updating UI
        self._update_timer = QTimer()
        self._update_timer.setInterval(100)  # Update every 100ms
        self._update_timer.timeout.connect(self._update_recording_status)

        self._connect_signals()

        # Set initial audio device
        initial_device = self._panel.get_selected_device()
        if initial_device:
            self._recorder.set_audio_input_device(initial_device)

    def _connect_signals(self) -> None:
        """Connect model and view signals"""
        # Panel signals
        self._panel.record_clicked.connect(self.start_recording)
        self._panel.pause_clicked.connect(self.pause_recording)
        self._panel.stop_clicked.connect(self.stop_recording)
        self._panel.device_changed.connect(self._on_device_changed)

        # Recorder signals
        self._recorder.recording_started.connect(self._on_recording_started)
        self._recorder.recording_stopped.connect(self._on_recording_stopped)
        self._recorder.recording_paused.connect(self._on_recording_paused)
        self._recorder.recording_resumed.connect(self._on_recording_resumed)
        self._recorder.error_occurred.connect(self._on_error)

        # Audio level monitor signals - for spectrogram
        self._recorder._level_monitor.audio_samples_ready.connect(
            self._on_audio_samples_ready
        )

        # Converter signals
        self._converter.conversion_completed.connect(self._on_conversion_completed)
        self._converter.conversion_failed.connect(self._on_conversion_failed)

    def start_recording(self) -> None:
        """Start a new recording"""
        if self._recorder.is_active():
            return

        # Generate filename
        filename = AudioUtils.generate_filename(extension=".wav")
        output_path = self._storage_dir / filename

        # Ensure storage directory exists
        self._storage_dir.mkdir(parents=True, exist_ok=True)

        # Start recording
        if self._recorder.start_recording(output_path):
            self._current_file = output_path
            self._waveform.set_recording_mode(True)

    def stop_recording(self) -> None:
        """Stop current recording"""
        if not self._recorder.is_active():
            return

        # Stop recording
        file_path = self._recorder.stop_recording()

        if file_path and self._codec_config and self._auto_convert:
            # Convert to target codec
            self._convert_recording(file_path)

    def pause_recording(self) -> None:
        """Pause current recording"""
        if self._recorder.is_recording():
            self._recorder.pause_recording()
        elif self._recorder.is_paused():
            self._recorder.resume_recording()

    def resume_recording(self) -> None:
        """Resume paused recording"""
        if self._recorder.is_paused():
            self._recorder.resume_recording()

    def set_codec_config(self, config: CodecConfig) -> None:
        """Set codec configuration for recordings

        Args:
            config: Codec configuration
        """
        self._codec_config = config

    def set_auto_convert(self, enabled: bool) -> None:
        """Enable/disable auto-conversion after recording

        Args:
            enabled: True to enable auto-conversion
        """
        self._auto_convert = enabled

    def set_keep_wav(self, keep: bool) -> None:
        """Set whether to keep original WAV file after conversion

        Args:
            keep: True to keep WAV file
        """
        self._keep_wav = keep

    def _convert_recording(self, wav_path: Path) -> None:
        """Convert WAV recording to target codec

        Args:
            wav_path: Path to WAV file
        """
        if not self._codec_config:
            return

        # Generate output path
        output_path = wav_path.with_suffix(self._codec_config.get_extension())

        # Convert
        self._converter.convert(
            input_path=wav_path,
            output_path=output_path,
            codec_config=self._codec_config,
        )

    def _update_recording_status(self) -> None:
        """Update recording status in UI"""
        if self._recorder.is_active():
            duration = self._recorder.get_recording_duration()
            self._panel.update_timer(duration)

            # Update audio level
            level = self._recorder.get_audio_level()
            self._panel.update_audio_level(level)

            # Add to live waveform buffer
            self._waveform_buffer.append(level)

            # Update waveform widget with live data
            if len(self._waveform_buffer) > 0:
                waveform_array = np.array(self._waveform_buffer)
                self._waveform.set_recording_buffer(waveform_array)

    # Signal handlers
    def _on_recording_started(self) -> None:
        """Handle recording started"""
        self._panel.set_recording_state(True)
        self._update_timer.start()

        # Initialize spectrogram for recording
        self._spectrogram_buffer.clear()
        self._frequency_bins = None
        self._spectrogram.set_recording_mode(True)

    def _on_recording_stopped(self, file_path: str) -> None:
        """Handle recording stopped

        Args:
            file_path: Path to recorded file
        """
        self._panel.set_recording_state(False)
        self._update_timer.stop()
        self._waveform.set_recording_mode(False)
        self._spectrogram.set_recording_mode(False)

        # Clear the live buffers
        self._waveform_buffer.clear()
        self._spectrogram_buffer.clear()
        self._frequency_bins = None

    def _on_recording_paused(self) -> None:
        """Handle recording paused"""
        self._panel.set_paused_state(True)

    def _on_recording_resumed(self) -> None:
        """Handle recording resumed"""
        self._panel.set_paused_state(False)

    def _on_conversion_completed(self, input_path: str, output_path: str) -> None:
        """Handle conversion completed

        Args:
            input_path: Input file path
            output_path: Output file path
        """
        # Delete original WAV if not keeping it
        if not self._keep_wav:
            try:
                Path(input_path).unlink()
            except Exception as e:
                print(f"Warning: Failed to delete WAV file: {e}")

    def _on_conversion_failed(self, file_path: str, error: str) -> None:
        """Handle conversion failed

        Args:
            file_path: File that failed to convert
            error: Error message
        """
        print(f"Conversion failed for {file_path}: {error}")

    def _on_error(self, error: str) -> None:
        """Handle recording error

        Args:
            error: Error message
        """
        print(f"Recording error: {error}")
        self._panel.set_recording_state(False)
        self._update_timer.stop()
        self._waveform.set_recording_mode(False)

    def _on_device_changed(self, device) -> None:
        """Handle audio input device change

        Args:
            device: QAudioDevice object
        """
        if device:
            self._recorder.set_audio_input_device(device)

    def _on_audio_samples_ready(self, samples: np.ndarray) -> None:
        """Process audio samples for spectrogram display

        Args:
            samples: 1D numpy array of audio samples (-1.0 to 1.0)
        """
        # Compute STFT slice for this audio chunk (medium quality)
        magnitude_slice = AudioUtils.compute_stft_slice(
            samples, sample_rate=48000, n_fft=1024, freq_min=80.0, freq_max=8000.0
        )

        if magnitude_slice is None:
            return

        # Store frequency bins on first slice
        if self._frequency_bins is None:
            # Calculate frequency bins for the filtered range
            n_fft = 1024
            sample_rate = 48000
            all_freqs = np.fft.rfftfreq(n_fft, 1.0 / sample_rate)
            mask = (all_freqs >= 80.0) & (all_freqs <= 8000.0)
            self._frequency_bins = all_freqs[mask]

        # Add to buffer
        self._spectrogram_buffer.append(magnitude_slice)

        # Limit buffer size
        if len(self._spectrogram_buffer) > self._max_spectrogram_slices:
            self._spectrogram_buffer.pop(0)

        # Update spectrogram widget
        if len(self._spectrogram_buffer) > 0:
            spec_matrix = np.array(self._spectrogram_buffer)
            self._spectrogram.set_spectrogram_data(spec_matrix, self._frequency_bins)
