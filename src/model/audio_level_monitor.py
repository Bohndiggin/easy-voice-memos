import struct
from pathlib import Path
from typing import Optional

import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal


class AudioLevelMonitor(QObject):
    """Monitors audio levels by polling the recording WAV file

    This approach avoids device access conflicts by reading the WAV file
    being written by QMediaRecorder in real-time, rather than trying to
    capture from the audio device simultaneously.
    """

    level_changed = Signal(float)  # Emits level 0.0-1.0
    audio_samples_ready = Signal(
        object
    )  # Emits np.ndarray of raw samples for spectrogram

    def __init__(self, parent: Optional[QObject] = None):
        """Initialize audio level monitor

        Args:
            parent: Parent QObject
        """
        super().__init__(parent)

        # Recording file tracking
        self._recording_file_path: Optional[Path] = None
        self._last_frame_position = 0

        # Level tracking
        self._current_level = 0.0
        self._smoothing_factor = 0.3  # Smooth level changes

        # Polling timer - fires every 50ms for responsive updates
        self._poll_timer = QTimer()
        self._poll_timer.setInterval(50)  # 50ms = 20Hz update rate
        self._poll_timer.timeout.connect(self._poll_wav_file)

    def start(self, file_path: Path) -> bool:
        """Start monitoring audio levels from recording file

        Args:
            file_path: Path to the WAV file being recorded

        Returns:
            True if started successfully
        """
        try:
            self._recording_file_path = file_path
            self._last_frame_position = 0
            self._current_level = 0.0

            # Start polling timer
            self._poll_timer.start()

            print(f"Audio level monitor started, polling file: {file_path}")
            return True

        except Exception as e:
            print(f"Error starting audio level monitor: {e}")
            import traceback

            traceback.print_exc()
            return False

    def stop(self) -> None:
        """Stop monitoring audio levels"""
        self._poll_timer.stop()
        self._recording_file_path = None
        self._last_frame_position = 0
        self._current_level = 0.0
        self.level_changed.emit(0.0)

    def get_current_level(self) -> float:
        """Get current audio level

        Returns:
            Level from 0.0 to 1.0
        """
        return self._current_level

    def _poll_wav_file(self) -> None:
        """Read latest audio data from recording WAV file

        This method is called by the timer every 50ms to read new audio
        frames from the WAV file and calculate the current audio level.

        Since the file is actively being written, we read it directly as
        raw bytes rather than using the wave module (which expects a
        complete file).
        """
        # Check if file exists and is accessible
        if not self._recording_file_path or not self._recording_file_path.exists():
            return

        try:
            # Read raw file data directly (wave module can't handle actively written files)
            with open(self._recording_file_path, "rb") as f:
                # Get file size
                f.seek(0, 2)  # Seek to end
                file_size = f.tell()

                # WAV header is 44 bytes - skip it
                # We assume 16-bit stereo PCM based on QMediaRecorder settings
                header_size = 44
                if file_size <= header_size:
                    # File not written enough yet
                    return

                # Calculate how many bytes to read (last 0.1 seconds of audio)
                # Assuming 48kHz stereo 16-bit: 48000 samples/sec * 2 channels * 2 bytes = 192000 bytes/sec
                # For 0.1 seconds: ~19200 bytes, but we'll use a conservative 8192 bytes
                bytes_to_read = min(8192, file_size - header_size)

                if bytes_to_read <= 0:
                    return

                # Read from near the end of the file
                read_position = file_size - bytes_to_read
                f.seek(read_position)
                audio_data = f.read(bytes_to_read)

                # Process the audio data
                # We assume 16-bit (sample_width=2) stereo (channels=2) based on recorder settings
                if len(audio_data) > 0:
                    self._process_audio_data(audio_data, sample_width=2, channels=2)

                    # Also emit raw samples for spectrogram
                    self._emit_raw_samples(audio_data)

        except (IOError, OSError) as e:
            # File may be locked by recorder or not fully written yet
            # Silently skip this poll cycle
            pass
        except Exception as e:
            # Unexpected error - log it with full traceback for debugging
            print(f"Error polling WAV file: {type(e).__name__}: {e}")
            import traceback

            traceback.print_exc()
            pass

    def _process_audio_data(
        self, data: bytes, sample_width: int, channels: int
    ) -> None:
        """Process audio data and calculate level

        Args:
            data: Raw audio data bytes
            sample_width: Bytes per sample (1=8-bit, 2=16-bit, etc.)
            channels: Number of audio channels
        """
        if len(data) == 0:
            return

        try:
            # Determine the format for struct unpacking
            bytes_per_frame = sample_width * channels
            frame_count = len(data) // bytes_per_frame

            if frame_count == 0:
                return

            # Unpack based on sample width
            if sample_width == 1:
                # 8-bit unsigned
                format_char = "B"
                max_value = 128.0
                samples = struct.unpack(
                    f"{frame_count * channels}{format_char}",
                    data[: frame_count * bytes_per_frame],
                )
                # Convert unsigned 8-bit to signed range
                audio_array = np.array(samples, dtype=np.float32) - 128.0
            elif sample_width == 2:
                # 16-bit signed
                format_char = "h"
                max_value = 32768.0
                samples = struct.unpack(
                    f"{frame_count * channels}{format_char}",
                    data[: frame_count * bytes_per_frame],
                )
                audio_array = np.array(samples, dtype=np.float32)
            elif sample_width == 3:
                # 24-bit (rare, convert to 32-bit)
                max_value = 8388608.0  # 2^23
                # Convert 24-bit to 32-bit integers
                audio_array = np.zeros(frame_count * channels, dtype=np.float32)
                for i in range(frame_count * channels):
                    byte_offset = i * 3
                    # Read 3 bytes and convert to signed 24-bit
                    value = int.from_bytes(
                        data[byte_offset : byte_offset + 3],
                        byteorder="little",
                        signed=True,
                    )
                    audio_array[i] = float(value)
            elif sample_width == 4:
                # 32-bit signed
                format_char = "i"
                max_value = 2147483648.0
                samples = struct.unpack(
                    f"{frame_count * channels}{format_char}",
                    data[: frame_count * bytes_per_frame],
                )
                audio_array = np.array(samples, dtype=np.float32)
            else:
                print(f"Unsupported sample width: {sample_width}")
                return

            # Normalize to -1.0 to 1.0 range
            audio_array = audio_array / max_value

            # If stereo, mix down to mono for level calculation
            if channels > 1:
                audio_array = audio_array.reshape(-1, channels).mean(axis=1)

            # Calculate RMS (Root Mean Square) level
            rms = np.sqrt(np.mean(audio_array**2))

            # Smooth the level for less jittery display
            self._current_level = (
                self._current_level * (1 - self._smoothing_factor)
                + rms * self._smoothing_factor
            )

            # Emit the level
            self.level_changed.emit(self._current_level)

        except Exception as e:
            print(
                f"Error processing audio data: {e}, data length: {len(data) if data else 0}"
            )
            pass

    def is_active(self) -> bool:
        """Check if monitor is active

        Returns:
            True if actively monitoring
        """
        return self._poll_timer.isActive()

    def _emit_raw_samples(self, audio_data: bytes) -> None:
        """Convert raw audio bytes to samples and emit for spectrogram

        Args:
            audio_data: Raw PCM audio bytes
        """
        try:
            # Convert bytes to 16-bit integers
            sample_count = len(audio_data) // 2  # 16-bit = 2 bytes per sample
            if sample_count == 0:
                return

            samples = struct.unpack(f"{sample_count}h", audio_data)

            # Convert to float32 numpy array and normalize to -1.0 to 1.0
            audio_array = np.array(samples, dtype=np.float32) / 32768.0

            # Mix stereo to mono for spectrogram (2 channels)
            # Reshape to [samples, 2] then average across channels
            if len(audio_array) >= 2:
                audio_array = audio_array.reshape(-1, 2).mean(axis=1)

            # Emit for spectrogram processing
            self.audio_samples_ready.emit(audio_array)

        except Exception as e:
            # Non-fatal error - just skip this emission
            pass
