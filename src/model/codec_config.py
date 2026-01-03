from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class CodecConfig:
    """Configuration for a specific audio codec"""

    codec_name: str  # User-friendly name: "mp3", "aac", "opus", etc.
    sample_rate: int  # Sample rate in Hz: 8000, 16000, 44100, 48000, etc.
    bit_rate: Optional[int] = None  # Bit rate in bps (None for lossless)
    channels: int = 1  # Number of channels: 1 (mono) or 2 (stereo)
    compression_level: Optional[int] = None  # For FLAC (0-8)

    def get_extension(self) -> str:
        """Get file extension for this codec

        Returns:
            File extension with dot (e.g., ".mp3")
        """
        extension_map = {
            "mp3": ".mp3",
            "aac": ".m4a",
            "opus": ".opus",
            "vorbis": ".ogg",
            "flac": ".flac",
            "wav": ".wav",
            "speex": ".spx",
            "amr": ".amr",
        }
        return extension_map.get(self.codec_name, ".wav")

    def get_ffmpeg_encoder(self) -> str:
        """Get FFmpeg encoder name for this codec

        Returns:
            FFmpeg encoder name (e.g., "libmp3lame")
        """
        encoder_map = {
            "mp3": "libmp3lame",
            "aac": "aac",
            "opus": "libopus",
            "vorbis": "libvorbis",
            "flac": "flac",
            "wav": "pcm_s16le",
            "speex": "libspeex",
            "amr": "libopencore_amrnb",
        }
        return encoder_map.get(self.codec_name, "pcm_s16le")

    def is_lossless(self) -> bool:
        """Check if codec is lossless

        Returns:
            True if lossless compression or uncompressed
        """
        return self.codec_name in ["flac", "wav"]

    def __str__(self) -> str:
        """String representation of codec config"""
        if self.is_lossless():
            return f"{self.codec_name.upper()} {self.sample_rate//1000}kHz {'Stereo' if self.channels == 2 else 'Mono'}"
        else:
            br = self.bit_rate // 1000 if self.bit_rate else 0
            return f"{self.codec_name.upper()} {self.sample_rate//1000}kHz {br}kbps {'Stereo' if self.channels == 2 else 'Mono'}"


class CodecPresets:
    """Predefined codec presets for common use cases"""

    # Voice recording presets (mono)
    VOICE_LOW = CodecConfig("opus", 16000, 24000, 1)  # Phone quality
    VOICE_STANDARD = CodecConfig("opus", 24000, 32000, 1)  # Standard voice
    VOICE_HIGH = CodecConfig("mp3", 44100, 128000, 1)  # High quality voice

    # Podcast presets
    PODCAST = CodecConfig("mp3", 44100, 96000, 1)  # Podcast standard

    # Music recording presets (stereo)
    MUSIC_STANDARD = CodecConfig("mp3", 44100, 192000, 2)  # Standard music
    MUSIC_HIGH = CodecConfig("aac", 48000, 256000, 2)  # High quality music
    MUSIC_LOSSLESS = CodecConfig(
        "flac", 48000, None, 2, compression_level=5
    )  # Lossless

    # Special purpose
    ARCHIVAL = CodecConfig(
        "flac", 48000, None, 2, compression_level=8
    )  # Maximum compression
    UNCOMPRESSED = CodecConfig("wav", 44100, None, 2)  # WAV uncompressed

    @classmethod
    def get_all_presets(cls) -> Dict[str, CodecConfig]:
        """Get all available presets

        Returns:
            Dictionary mapping preset names to CodecConfig objects
        """
        return {
            "Voice - Low Quality": cls.VOICE_LOW,
            "Voice - Standard": cls.VOICE_STANDARD,
            "Voice - High Quality": cls.VOICE_HIGH,
            "Podcast Standard": cls.PODCAST,
            "Music - Standard": cls.MUSIC_STANDARD,
            "Music - High Quality": cls.MUSIC_HIGH,
            "Music - Lossless": cls.MUSIC_LOSSLESS,
            "Archival - Maximum Compression": cls.ARCHIVAL,
            "Uncompressed WAV": cls.UNCOMPRESSED,
        }

    @staticmethod
    def get_codec_info(codec_name: str) -> Dict[str, any]:
        """Get detailed information about a codec

        Args:
            codec_name: Codec name (e.g., "mp3", "opus")

        Returns:
            Dictionary with codec information:
            - extensions: List of valid file extensions
            - description: Human-readable description
            - lossy: Boolean indicating if codec is lossy
            - ffmpeg_encoder: FFmpeg encoder name
            - supported_sample_rates: List of common sample rates
            - supported_bit_rates: List of common bit rates (None for lossless)
        """
        codec_info_map = {
            "mp3": {
                "extensions": [".mp3"],
                "description": "MPEG Audio Layer 3 - Universal compatibility",
                "lossy": True,
                "ffmpeg_encoder": "libmp3lame",
                "supported_sample_rates": [8000, 16000, 22050, 44100, 48000],
                "supported_bit_rates": [
                    64000,
                    96000,
                    128000,
                    160000,
                    192000,
                    256000,
                    320000,
                ],
            },
            "aac": {
                "extensions": [".m4a", ".aac"],
                "description": "Advanced Audio Coding - Modern mobile standard",
                "lossy": True,
                "ffmpeg_encoder": "aac",
                "supported_sample_rates": [8000, 16000, 22050, 44100, 48000],
                "supported_bit_rates": [64000, 96000, 128000, 192000, 256000],
            },
            "opus": {
                "extensions": [".opus"],
                "description": "Opus - Best quality/size ratio for voice",
                "lossy": True,
                "ffmpeg_encoder": "libopus",
                "supported_sample_rates": [8000, 12000, 16000, 24000, 48000],
                "supported_bit_rates": [16000, 24000, 32000, 64000, 96000, 128000],
            },
            "vorbis": {
                "extensions": [".ogg", ".oga"],
                "description": "Ogg Vorbis - Open-source alternative to MP3",
                "lossy": True,
                "ffmpeg_encoder": "libvorbis",
                "supported_sample_rates": [8000, 16000, 22050, 44100, 48000],
                "supported_bit_rates": [
                    64000,
                    80000,
                    96000,
                    112000,
                    128000,
                    160000,
                    192000,
                    256000,
                ],
            },
            "flac": {
                "extensions": [".flac"],
                "description": "Free Lossless Audio Codec - Archival quality",
                "lossy": False,
                "ffmpeg_encoder": "flac",
                "supported_sample_rates": [8000, 16000, 22050, 44100, 48000, 96000],
                "supported_bit_rates": None,
                "compression_levels": [0, 1, 2, 3, 4, 5, 6, 7, 8],
            },
            "wav": {
                "extensions": [".wav"],
                "description": "WAV - Uncompressed PCM audio",
                "lossy": False,
                "ffmpeg_encoder": "pcm_s16le",
                "supported_sample_rates": [8000, 16000, 22050, 44100, 48000, 96000],
                "supported_bit_rates": None,
            },
            "speex": {
                "extensions": [".spx"],
                "description": "Speex - Voice-optimized codec",
                "lossy": True,
                "ffmpeg_encoder": "libspeex",
                "supported_sample_rates": [8000, 16000, 32000],
                "supported_bit_rates": [8000, 16000, 24000, 32000],
            },
            "amr": {
                "extensions": [".amr"],
                "description": "AMR - Ultra-low bitrate voice codec",
                "lossy": True,
                "ffmpeg_encoder": "libopencore_amrnb",
                "supported_sample_rates": [8000],
                "supported_bit_rates": [
                    4750,
                    5150,
                    5900,
                    6700,
                    7400,
                    7950,
                    10200,
                    12200,
                ],
            },
        }

        return codec_info_map.get(
            codec_name,
            {
                "extensions": [".wav"],
                "description": "Unknown codec",
                "lossy": False,
                "ffmpeg_encoder": "pcm_s16le",
                "supported_sample_rates": [44100],
                "supported_bit_rates": None,
            },
        )

    @staticmethod
    def get_all_codecs() -> List[str]:
        """Get list of all supported codec names

        Returns:
            List of codec names
        """
        return ["mp3", "aac", "opus", "vorbis", "flac", "wav", "speex", "amr"]


# Codec configuration matrix for validation
CODEC_CONFIGS = {
    "mp3": {
        "encoder": "libmp3lame",
        "extension": ".mp3",
        "sample_rates": [8000, 16000, 22050, 44100, 48000],
        "bit_rates": [64000, 96000, 128000, 160000, 192000, 256000, 320000],
        "channels": [1, 2],
    },
    "aac": {
        "encoder": "aac",
        "extension": ".m4a",
        "sample_rates": [8000, 16000, 22050, 44100, 48000],
        "bit_rates": [64000, 96000, 128000, 192000, 256000],
        "channels": [1, 2],
    },
    "opus": {
        "encoder": "libopus",
        "extension": ".opus",
        "sample_rates": [8000, 12000, 16000, 24000, 48000],
        "bit_rates": [16000, 24000, 32000, 64000, 96000, 128000],
        "channels": [1, 2],
    },
    "vorbis": {
        "encoder": "libvorbis",
        "extension": ".ogg",
        "sample_rates": [8000, 16000, 22050, 44100, 48000],
        "bit_rates": [64000, 80000, 96000, 112000, 128000, 160000, 192000, 256000],
        "channels": [1, 2],
    },
    "flac": {
        "encoder": "flac",
        "extension": ".flac",
        "sample_rates": [8000, 16000, 22050, 44100, 48000, 96000],
        "bit_rates": None,  # Lossless
        "channels": [1, 2],
        "compression_levels": [0, 1, 2, 3, 4, 5, 6, 7, 8],
    },
    "wav": {
        "encoder": "pcm_s16le",
        "extension": ".wav",
        "sample_rates": [8000, 16000, 22050, 44100, 48000, 96000],
        "bit_rates": None,  # Uncompressed
        "channels": [1, 2],
    },
}
