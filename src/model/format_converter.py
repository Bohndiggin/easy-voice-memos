from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QObject, Signal

from src.model.codec_config import CodecConfig
from src.utils.ffmpeg_wrapper import FFmpegWrapper


class FormatConverter(QObject):
    """Converts audio files between different formats using FFmpeg"""

    # Signals
    conversion_started = Signal(str)  # file_path
    conversion_progress = Signal(str, float)  # file_path, progress (0.0-1.0)
    conversion_completed = Signal(str, str)  # input_path, output_path
    conversion_failed = Signal(str, str)  # file_path, error_message

    def __init__(self, parent: Optional[QObject] = None):
        """Initialize format converter

        Args:
            parent: Parent QObject
        """
        super().__init__(parent)
        self._ffmpeg = FFmpegWrapper()
        self._is_converting = False
        self._current_file: Optional[Path] = None

    def convert(
        self, input_path: Path, output_path: Path, codec_config: CodecConfig
    ) -> bool:
        """Convert an audio file to a different format

        Args:
            input_path: Input file path
            output_path: Output file path
            codec_config: Target codec configuration

        Returns:
            True if conversion started successfully
        """
        if self._is_converting:
            self.conversion_failed.emit(
                str(input_path), "Another conversion is already in progress"
            )
            return False

        if not input_path.exists():
            self.conversion_failed.emit(str(input_path), "Input file not found")
            return False

        try:
            self._is_converting = True
            self._current_file = input_path

            self.conversion_started.emit(str(input_path))

            # Build conversion arguments
            extra_args = []
            if codec_config.compression_level is not None:
                extra_args.extend(
                    ["-compression_level", str(codec_config.compression_level)]
                )

            # Perform conversion
            success, error_msg = self._ffmpeg.convert_format(
                input_path=input_path,
                output_path=output_path,
                codec=codec_config.get_ffmpeg_encoder(),
                sample_rate=codec_config.sample_rate,
                bit_rate=codec_config.bit_rate,
                channels=codec_config.channels,
                extra_args=extra_args if extra_args else None,
            )

            if success:
                self.conversion_completed.emit(str(input_path), str(output_path))
            else:
                self.conversion_failed.emit(str(input_path), error_msg)

            return success

        except Exception as e:
            self.conversion_failed.emit(str(input_path), str(e))
            return False

        finally:
            self._is_converting = False
            self._current_file = None

    def convert_in_place(
        self, file_path: Path, codec_config: CodecConfig, keep_original: bool = False
    ) -> Optional[Path]:
        """Convert a file and replace the original (or keep both)

        Args:
            file_path: File to convert
            codec_config: Target codec configuration
            keep_original: If True, keep the original file

        Returns:
            Path to converted file or None if failed
        """
        if not file_path.exists():
            self.conversion_failed.emit(str(file_path), "File not found")
            return None

        # Generate output path
        output_path = file_path.with_suffix(codec_config.get_extension())

        # If output would have same name, add suffix
        if output_path == file_path:
            output_path = file_path.with_name(
                f"{file_path.stem}_converted{codec_config.get_extension()}"
            )

        # Convert
        success = self.convert(file_path, output_path, codec_config)

        if success and not keep_original and output_path != file_path:
            try:
                # Delete original
                file_path.unlink()
            except Exception as e:
                print(f"Warning: Failed to delete original file: {e}")

        return output_path if success else None

    def batch_convert(
        self,
        files: List[Path],
        codec_config: CodecConfig,
        output_dir: Optional[Path] = None,
    ) -> int:
        """Convert multiple files to the same format

        Args:
            files: List of input files
            codec_config: Target codec configuration
            output_dir: Output directory (None = same as input)

        Returns:
            Number of successful conversions
        """
        success_count = 0

        for file_path in files:
            if not file_path.exists():
                continue

            # Determine output path
            if output_dir:
                output_path = (
                    output_dir / f"{file_path.stem}{codec_config.get_extension()}"
                )
            else:
                output_path = file_path.with_suffix(codec_config.get_extension())

            # Convert
            if self.convert(file_path, output_path, codec_config):
                success_count += 1

        return success_count

    def is_converting(self) -> bool:
        """Check if a conversion is in progress

        Returns:
            True if converting
        """
        return self._is_converting

    def get_current_file(self) -> Optional[Path]:
        """Get the file currently being converted

        Returns:
            Path to current file or None
        """
        return self._current_file

    def cancel_conversion(self) -> bool:
        """Cancel current conversion

        Note: Currently not implemented as FFmpeg runs synchronously.
        Would require running FFmpeg in a separate thread/process.

        Returns:
            False (not implemented)
        """
        # TODO: Implement cancellation using QProcess or threading
        return False

    def get_conversion_estimate(
        self, input_path: Path, codec_config: CodecConfig
    ) -> dict:
        """Estimate output file size and time

        Args:
            input_path: Input file path
            codec_config: Target codec configuration

        Returns:
            Dictionary with 'estimated_size' and 'estimated_time' (placeholder)
        """
        if not input_path.exists():
            return {"estimated_size": 0, "estimated_time": 0}

        # Get input file info
        info = self._ffmpeg.get_audio_info(input_path)
        duration = info.get("duration", 0)

        # Estimate output size
        if codec_config.bit_rate:
            # For lossy codecs
            estimated_size = int((codec_config.bit_rate * duration) / 8)
        else:
            # For lossless (rough estimate)
            estimated_size = int(
                duration * codec_config.sample_rate * 2 * codec_config.channels
            )

        # Rough time estimate (very approximate)
        # Assumes conversion at 10x realtime speed
        estimated_time = duration / 10.0

        return {"estimated_size": estimated_size, "estimated_time": estimated_time}
