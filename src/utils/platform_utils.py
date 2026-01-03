import os
import platform
import subprocess
from pathlib import Path
from typing import List


class PlatformUtils:
    """Cross-platform compatibility helpers"""

    @staticmethod
    def get_default_storage_dir() -> Path:
        """Get the default directory for storing voice memos

        Returns:
            Path to default storage directory:
            - Linux: ~/Documents/VoiceMemos
            - Windows: %USERPROFILE%\\Documents\\VoiceMemos
            - macOS: ~/Documents/VoiceMemos
        """
        home = Path.home()
        storage_dir = home / "Documents" / "VoiceMemos"
        storage_dir.mkdir(parents=True, exist_ok=True)
        return storage_dir

    @staticmethod
    def get_config_dir() -> Path:
        """Get the configuration directory for app settings

        Returns:
            Path to config directory:
            - Linux: ~/.config/voice-memos
            - Windows: %APPDATA%\\VoiceMemos
            - macOS: ~/Library/Application Support/VoiceMemos
        """
        system = platform.system()

        if system == "Windows":
            appdata = Path(
                os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
            )
            config_dir = appdata / "VoiceMemos"
        elif system == "Darwin":  # macOS
            config_dir = Path.home() / "Library" / "Application Support" / "VoiceMemos"
        else:  # Linux and others
            config_dir = Path.home() / ".config" / "voice-memos"

        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    @staticmethod
    def open_file_manager(path: Path) -> None:
        """Open the system file manager at the specified path

        Args:
            path: Directory or file path to open
        """
        system = platform.system()
        path_str = str(path.resolve())

        try:
            if system == "Windows":
                subprocess.run(["explorer", path_str], check=False)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", path_str], check=False)
            else:  # Linux
                subprocess.run(["xdg-open", path_str], check=False)
        except Exception as e:
            print(f"Failed to open file manager: {e}")

    @staticmethod
    def get_audio_input_devices() -> List[str]:
        """Get list of available audio input devices

        Returns:
            List of device names/identifiers

        Note:
            This is a placeholder. PySide6's QMediaDevices will be used
            for actual device enumeration in the audio_recorder module.
        """
        return ["default"]
