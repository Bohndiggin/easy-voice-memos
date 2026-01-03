import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np


class FFmpegWrapper:
    """Wrapper for FFmpeg subprocess operations"""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        """Initialize FFmpeg wrapper

        Args:
            ffmpeg_path: Path to ffmpeg executable (default: "ffmpeg" from PATH)
            ffprobe_path: Path to ffprobe executable (default: "ffprobe" from PATH)
        """
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    def check_availability(self) -> bool:
        """Check if FFmpeg is available on the system

        Returns:
            True if FFmpeg is available and executable
        """
        return shutil.which(self.ffmpeg_path) is not None

    def get_version(self) -> str:
        """Get FFmpeg version string

        Returns:
            Version string or "Unknown" if FFmpeg is not available
        """
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            # First line contains version info
            first_line = result.stdout.split("\n")[0]
            return first_line
        except (subprocess.SubprocessError, FileNotFoundError):
            return "Unknown"

    def get_supported_codecs(self) -> Dict[str, List[str]]:
        """Get list of supported encoders and decoders

        Returns:
            Dictionary with 'encoders' and 'decoders' keys containing codec lists
        """
        codecs = {"encoders": [], "decoders": []}

        try:
            # Get encoders
            result = subprocess.run(
                [self.ffmpeg_path, "-encoders"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            for line in result.stdout.split("\n"):
                if line.strip() and line.startswith(" "):
                    parts = line.split()
                    if len(parts) >= 2:
                        codec_name = parts[1]
                        codecs["encoders"].append(codec_name)

        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        return codecs

    def get_audio_info(self, file_path: Path) -> Dict[str, any]:
        """Extract audio metadata from file using ffprobe

        Args:
            file_path: Path to audio file

        Returns:
            Dictionary containing:
            - codec: Codec name
            - sample_rate: Sample rate in Hz
            - bit_rate: Bit rate in bps (None if not available)
            - duration: Duration in seconds
            - channels: Number of audio channels
            - format: Container format
        """
        info = {
            "codec": "unknown",
            "sample_rate": 0,
            "bit_rate": None,
            "duration": 0.0,
            "channels": 0,
            "format": "unknown",
        }

        try:
            result = subprocess.run(
                [
                    self.ffprobe_path,
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    str(file_path),
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )

            data = json.loads(result.stdout)

            # Get format info
            if "format" in data:
                info["format"] = data["format"].get("format_name", "unknown")
                info["duration"] = float(data["format"].get("duration", 0.0))
                if "bit_rate" in data["format"]:
                    info["bit_rate"] = int(data["format"]["bit_rate"])

            # Get first audio stream info
            if "streams" in data:
                for stream in data["streams"]:
                    if stream.get("codec_type") == "audio":
                        info["codec"] = stream.get("codec_name", "unknown")
                        info["sample_rate"] = int(stream.get("sample_rate", 0))
                        info["channels"] = int(stream.get("channels", 0))
                        if "bit_rate" in stream and info["bit_rate"] is None:
                            info["bit_rate"] = int(stream["bit_rate"])
                        break

        except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
            pass

        return info

    def convert_format(
        self,
        input_path: Path,
        output_path: Path,
        codec: str,
        sample_rate: Optional[int] = None,
        bit_rate: Optional[int] = None,
        channels: Optional[int] = None,
        extra_args: Optional[List[str]] = None,
    ) -> Tuple[bool, str]:
        """Convert audio file to different format/codec

        Args:
            input_path: Input file path
            output_path: Output file path
            codec: FFmpeg codec name (e.g., "libmp3lame", "libopus")
            sample_rate: Target sample rate in Hz (optional)
            bit_rate: Target bit rate in bps (optional)
            channels: Number of channels (optional)
            extra_args: Additional FFmpeg arguments (optional)

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        cmd = [self.ffmpeg_path, "-i", str(input_path), "-y"]

        # Audio codec
        cmd.extend(["-c:a", codec])

        # Sample rate
        if sample_rate:
            cmd.extend(["-ar", str(sample_rate)])

        # Bit rate
        if bit_rate:
            cmd.extend(["-b:a", str(bit_rate)])

        # Channels
        if channels:
            cmd.extend(["-ac", str(channels)])

        # Extra arguments
        if extra_args:
            cmd.extend(extra_args)

        # Output file
        cmd.append(str(output_path))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=300,  # 5 minute timeout
            )
            return True, ""
        except subprocess.CalledProcessError as e:
            return False, e.stderr
        except subprocess.TimeoutExpired:
            return False, "Conversion timed out"
        except FileNotFoundError:
            return False, "FFmpeg not found"

    def extract_audio_samples(
        self,
        file_path: Path,
        sample_rate: int = 48000,
        channels: int = 1,
        max_duration: Optional[float] = None,
    ) -> Optional[np.ndarray]:
        """Extract raw audio samples from audio file

        Args:
            file_path: Path to audio file
            sample_rate: Target sample rate in Hz
            channels: Number of channels (1=mono, 2=stereo)
            max_duration: Maximum duration to process in seconds (optional)

        Returns:
            Numpy array of audio samples (normalized -1.0 to 1.0)
            or None if extraction fails
        """
        try:
            # Build ffmpeg command to extract PCM data
            cmd = [
                self.ffmpeg_path,
                "-i",
                str(file_path),
                "-f",
                "f32le",  # 32-bit float PCM
                "-ac",
                str(channels),
                "-ar",
                str(sample_rate),
            ]

            if max_duration:
                cmd.extend(["-t", str(max_duration)])

            cmd.append("-")  # Output to stdout

            # Run ffmpeg
            result = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
            )

            if result.returncode != 0:
                return None

            # Convert bytes to numpy array
            audio_data = np.frombuffer(result.stdout, dtype=np.float32)

            # If stereo, reshape to [samples, channels]
            if channels == 2 and len(audio_data) > 0:
                audio_data = audio_data.reshape(-1, 2)

            return audio_data

        except Exception as e:
            print(f"Error extracting audio samples: {e}")
            return None

    def extract_waveform_data(
        self,
        file_path: Path,
        resolution: int = 1000,
        max_duration: Optional[float] = None,
    ) -> Optional[np.ndarray]:
        """Extract waveform amplitude data from audio file

        Args:
            file_path: Path to audio file
            resolution: Number of sample points to extract
            max_duration: Maximum duration to process in seconds (optional)

        Returns:
            Numpy array of amplitude values (normalized -1.0 to 1.0)
            or None if extraction fails
        """
        try:
            # Build ffmpeg command to extract PCM data
            cmd = [
                self.ffmpeg_path,
                "-i",
                str(file_path),
                "-f",
                "f32le",  # 32-bit float PCM
                "-ac",
                "1",  # Mono
                "-ar",
                "4000",  # 4kHz sample rate (sufficient for visualization)
            ]

            if max_duration:
                cmd.extend(["-t", str(max_duration)])

            cmd.append("-")  # Output to stdout

            result = subprocess.run(cmd, capture_output=True, check=True, timeout=30)

            # Convert bytes to numpy array
            audio_data = np.frombuffer(result.stdout, dtype=np.float32)

            if len(audio_data) == 0:
                return None

            # Downsample to target resolution
            if len(audio_data) > resolution:
                # Calculate chunk size
                chunk_size = len(audio_data) // resolution

                # Reshape and take max absolute value in each chunk
                chunks = len(audio_data) // chunk_size
                trimmed = audio_data[: chunks * chunk_size]
                reshaped = trimmed.reshape(chunks, chunk_size)
                waveform = np.max(np.abs(reshaped), axis=1)[:resolution]
            else:
                waveform = np.abs(audio_data)

            return waveform

        except subprocess.SubprocessError as e:
            print(f"FFmpeg error extracting waveform: {e}")
            return None
        except FileNotFoundError as e:
            print(f"File not found when extracting waveform: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error extracting waveform: {e}")
            return None

    def build_ffmpeg_command(
        self, input_file: Path, output_file: Path, **params
    ) -> List[str]:
        """Build FFmpeg command with parameters

        Args:
            input_file: Input file path
            output_file: Output file path
            **params: Codec parameters

        Returns:
            List of command arguments
        """
        cmd = [self.ffmpeg_path, "-i", str(input_file), "-y"]

        if "codec" in params:
            cmd.extend(["-c:a", params["codec"]])
        if "sample_rate" in params:
            cmd.extend(["-ar", str(params["sample_rate"])])
        if "bit_rate" in params:
            cmd.extend(["-b:a", str(params["bit_rate"])])
        if "channels" in params:
            cmd.extend(["-ac", str(params["channels"])])
        if "compression_level" in params:
            cmd.extend(["-compression_level", str(params["compression_level"])])

        cmd.append(str(output_file))
        return cmd
