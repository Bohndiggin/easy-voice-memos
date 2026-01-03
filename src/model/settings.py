import json
from pathlib import Path
from typing import Any, Dict, Optional

from src.model.codec_config import CodecConfig, CodecPresets
from src.utils.platform_utils import PlatformUtils


class AppSettings:
    """Application settings persistence using JSON"""

    def __init__(self, config_file: Optional[Path] = None):
        """Initialize settings manager

        Args:
            config_file: Path to settings file (default: platform-specific config dir)
        """
        if config_file is None:
            config_dir = PlatformUtils.get_config_dir()
            config_file = config_dir / "settings.json"

        self.config_file = Path(config_file)
        self._settings: Dict[str, Any] = {}
        self._default_settings = self._get_default_settings()

        # Load existing settings or create defaults
        self.load()

    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default settings

        Returns:
            Dictionary of default settings
        """
        return {
            "default_codec": {
                "codec_name": "opus",
                "sample_rate": 24000,
                "bit_rate": 32000,
                "channels": 1,
                "compression_level": None,
            },
            "storage_directory": str(PlatformUtils.get_default_storage_dir()),
            "window_geometry": {
                "width": 900,
                "height": 700,
                "x": None,
                "y": None,
            },
            "theme": "default",
            "auto_convert_after_recording": True,
            "keep_original_wav": False,
            "show_waveform": True,
            "default_file_prefix": "memo",
            "last_preset": "Voice - Standard",
            "custom_presets": {},  # Dictionary of custom preset name -> codec config dict
        }

    def load(self) -> Dict[str, Any]:
        """Load settings from file

        Returns:
            Dictionary of settings
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    loaded_settings = json.load(f)
                    # Merge with defaults (in case new settings were added)
                    self._settings = {**self._default_settings, **loaded_settings}
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load settings: {e}")
                self._settings = self._default_settings.copy()
        else:
            self._settings = self._default_settings.copy()
            self.save()  # Create default settings file

        return self._settings

    def save(self) -> bool:
        """Save current settings to file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure config directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, "w") as f:
                json.dump(self._settings, f, indent=2)
            return True
        except IOError as e:
            print(f"Error: Failed to save settings: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value

        Args:
            key: Setting key (supports dot notation, e.g., "window_geometry.width")
            default: Default value if key doesn't exist

        Returns:
            Setting value or default
        """
        # Support dot notation for nested settings
        keys = key.split(".")
        value = self._settings

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """Set a setting value

        Args:
            key: Setting key (supports dot notation)
            value: Value to set
        """
        # Support dot notation for nested settings
        keys = key.split(".")

        if len(keys) == 1:
            self._settings[key] = value
        else:
            # Navigate to nested dictionary
            current = self._settings
            for k in keys[:-1]:
                if k not in current or not isinstance(current[k], dict):
                    current[k] = {}
                current = current[k]
            current[keys[-1]] = value

    def get_codec_config(self) -> CodecConfig:
        """Get the default codec configuration

        Returns:
            CodecConfig object
        """
        codec_dict = self.get("default_codec", {})
        return CodecConfig(
            codec_name=codec_dict.get("codec_name", "opus"),
            sample_rate=codec_dict.get("sample_rate", 24000),
            bit_rate=codec_dict.get("bit_rate", 32000),
            channels=codec_dict.get("channels", 1),
            compression_level=codec_dict.get("compression_level"),
        )

    def set_codec_config(self, config: CodecConfig) -> None:
        """Set the default codec configuration

        Args:
            config: CodecConfig object
        """
        self.set(
            "default_codec",
            {
                "codec_name": config.codec_name,
                "sample_rate": config.sample_rate,
                "bit_rate": config.bit_rate,
                "channels": config.channels,
                "compression_level": config.compression_level,
            },
        )

    def get_storage_directory(self) -> Path:
        """Get the storage directory for voice memos

        Returns:
            Path to storage directory
        """
        storage_dir = Path(
            self.get("storage_directory", PlatformUtils.get_default_storage_dir())
        )
        storage_dir.mkdir(parents=True, exist_ok=True)
        return storage_dir

    def set_storage_directory(self, path: Path) -> None:
        """Set the storage directory

        Args:
            path: Path to storage directory
        """
        self.set("storage_directory", str(path))

    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults"""
        self._settings = self._default_settings.copy()
        self.save()

    def get_all(self) -> Dict[str, Any]:
        """Get all settings

        Returns:
            Dictionary of all settings
        """
        return self._settings.copy()

    def add_custom_preset(self, name: str, config: CodecConfig) -> bool:
        """Add a custom preset

        Args:
            name: Preset name
            config: Codec configuration

        Returns:
            True if added successfully
        """
        custom_presets = self.get("custom_presets", {})

        # Don't allow overwriting built-in presets
        if name in CodecPresets.get_all_presets():
            return False

        custom_presets[name] = {
            "codec_name": config.codec_name,
            "sample_rate": config.sample_rate,
            "bit_rate": config.bit_rate,
            "channels": config.channels,
            "compression_level": config.compression_level,
        }

        self.set("custom_presets", custom_presets)
        self.save()
        return True

    def remove_custom_preset(self, name: str) -> bool:
        """Remove a custom preset

        Args:
            name: Preset name

        Returns:
            True if removed successfully
        """
        custom_presets = self.get("custom_presets", {})

        if name in custom_presets:
            del custom_presets[name]
            self.set("custom_presets", custom_presets)
            self.save()
            return True

        return False

    def get_custom_presets(self) -> Dict[str, CodecConfig]:
        """Get all custom presets

        Returns:
            Dictionary of preset name -> CodecConfig
        """
        custom_presets = self.get("custom_presets", {})
        result = {}

        for name, config_dict in custom_presets.items():
            result[name] = CodecConfig(
                codec_name=config_dict.get("codec_name", "opus"),
                sample_rate=config_dict.get("sample_rate", 24000),
                bit_rate=config_dict.get("bit_rate"),
                channels=config_dict.get("channels", 1),
                compression_level=config_dict.get("compression_level"),
            )

        return result

    def get_all_presets(self) -> Dict[str, CodecConfig]:
        """Get all presets (built-in + custom)

        Returns:
            Dictionary of all presets
        """

        # Start with built-in presets
        all_presets = CodecPresets.get_all_presets().copy()

        # Add custom presets
        all_presets.update(self.get_custom_presets())

        return all_presets
