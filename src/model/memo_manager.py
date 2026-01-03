import shutil
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QObject, Signal

from src.utils.ffmpeg_wrapper import FFmpegWrapper


@dataclass
class VoiceMemo:
    """Metadata for a voice memo recording"""

    id: str  # Unique identifier (UUID)
    filename: str  # Display name
    file_path: str  # Absolute path to file
    duration: float  # Duration in seconds
    codec: str  # Codec name
    sample_rate: int  # Sample rate in Hz
    bit_rate: Optional[int]  # Bit rate in bps (None for lossless)
    file_size: int  # File size in bytes
    created_at: str  # ISO format datetime
    modified_at: str  # ISO format datetime

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "VoiceMemo":
        """Create from dictionary"""
        return cls(**data)


class MemoManager(QObject):
    """Manages voice memo files and metadata"""

    # Signals
    memo_added = Signal(object)  # VoiceMemo
    memo_removed = Signal(str)  # memo_id
    memo_updated = Signal(object)  # VoiceMemo
    scan_completed = Signal(int)  # number of memos found

    def __init__(self, storage_dir: Path, parent: Optional[QObject] = None):
        """Initialize memo manager

        Args:
            storage_dir: Directory where memos are stored
            parent: Parent QObject
        """
        super().__init__(parent)

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self._ffmpeg = FFmpegWrapper()
        self._memos: dict[str, VoiceMemo] = {}

        # Initial scan
        self.scan_directory()

    def scan_directory(self) -> int:
        """Scan storage directory for audio files

        Returns:
            Number of memos found
        """
        self._memos.clear()

        # Audio file extensions
        audio_extensions = {
            ".wav",
            ".mp3",
            ".m4a",
            ".aac",
            ".opus",
            ".ogg",
            ".flac",
            ".spx",
            ".amr",
        }

        # Find all audio files
        for file_path in self.storage_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in audio_extensions:
                try:
                    memo = self._create_memo_from_file(file_path)
                    if memo:
                        self._memos[memo.id] = memo
                except Exception as e:
                    print(f"Warning: Failed to process {file_path}: {e}")

        count = len(self._memos)
        self.scan_completed.emit(count)
        return count

    def _create_memo_from_file(self, file_path: Path) -> Optional[VoiceMemo]:
        """Create VoiceMemo object from audio file

        Args:
            file_path: Path to audio file

        Returns:
            VoiceMemo object or None if failed
        """
        try:
            # Get file stats
            stats = file_path.stat()
            file_size = stats.st_size
            created_at = datetime.fromtimestamp(stats.st_ctime)
            modified_at = datetime.fromtimestamp(stats.st_mtime)

            # Get audio info from FFmpeg
            audio_info = self._ffmpeg.get_audio_info(file_path)

            # Create memo
            memo = VoiceMemo(
                id=str(uuid.uuid4()),
                filename=file_path.stem,  # Without extension
                file_path=str(file_path.absolute()),
                duration=audio_info.get("duration", 0.0),
                codec=audio_info.get("codec", "unknown"),
                sample_rate=audio_info.get("sample_rate", 0),
                bit_rate=audio_info.get("bit_rate"),
                file_size=file_size,
                created_at=created_at.isoformat(),
                modified_at=modified_at.isoformat(),
            )

            return memo

        except Exception as e:
            print(f"Error creating memo from {file_path}: {e}")
            return None

    def list_memos(self) -> List[VoiceMemo]:
        """Get list of all memos

        Returns:
            List of VoiceMemo objects, sorted by creation date (newest first)
        """
        memos = list(self._memos.values())
        memos.sort(key=lambda m: m.created_at, reverse=True)
        return memos

    def get_memo(self, memo_id: str) -> Optional[VoiceMemo]:
        """Get a specific memo by ID

        Args:
            memo_id: Memo ID

        Returns:
            VoiceMemo object or None if not found
        """
        return self._memos.get(memo_id)

    def add_memo(self, file_path: Path) -> Optional[VoiceMemo]:
        """Add a new memo to the manager

        Args:
            file_path: Path to audio file

        Returns:
            VoiceMemo object or None if failed
        """
        memo = self._create_memo_from_file(file_path)
        if memo:
            self._memos[memo.id] = memo
            self.memo_added.emit(memo)
        return memo

    def rename_memo(self, memo_id: str, new_name: str) -> bool:
        """Rename a memo

        Args:
            memo_id: Memo ID
            new_name: New display name (without extension)

        Returns:
            True if successful
        """
        memo = self._memos.get(memo_id)
        if not memo:
            return False

        try:
            old_path = Path(memo.file_path)
            new_path = old_path.parent / f"{new_name}{old_path.suffix}"

            # Rename file
            old_path.rename(new_path)

            # Update memo
            memo.filename = new_name
            memo.file_path = str(new_path.absolute())
            memo.modified_at = datetime.now().isoformat()

            self.memo_updated.emit(memo)
            return True

        except Exception as e:
            print(f"Error renaming memo: {e}")
            return False

    def delete_memo(self, memo_id: str) -> bool:
        """Delete a memo and its file

        Args:
            memo_id: Memo ID

        Returns:
            True if successful
        """
        memo = self._memos.get(memo_id)
        if not memo:
            return False

        try:
            # Delete file
            file_path = Path(memo.file_path)
            if file_path.exists():
                file_path.unlink()

            # Remove from manager
            del self._memos[memo_id]
            self.memo_removed.emit(memo_id)
            return True

        except Exception as e:
            print(f"Error deleting memo: {e}")
            return False

    def import_memo(self, source_path: Path) -> Optional[VoiceMemo]:
        """Import an audio file from outside storage directory

        Args:
            source_path: Path to source audio file

        Returns:
            VoiceMemo object or None if failed
        """
        try:
            # Generate destination path
            dest_path = self.storage_dir / source_path.name

            # Handle name conflicts
            counter = 1
            while dest_path.exists():
                stem = source_path.stem
                suffix = source_path.suffix
                dest_path = self.storage_dir / f"{stem}_{counter}{suffix}"
                counter += 1

            # Copy file
            shutil.copy2(source_path, dest_path)

            # Add to manager
            return self.add_memo(dest_path)

        except Exception as e:
            print(f"Error importing memo: {e}")
            return None

    def export_memo(self, memo_id: str, dest_path: Path) -> bool:
        """Export a memo to a different location

        Args:
            memo_id: Memo ID
            dest_path: Destination path

        Returns:
            True if successful
        """
        memo = self._memos.get(memo_id)
        if not memo:
            return False

        try:
            source_path = Path(memo.file_path)
            shutil.copy2(source_path, dest_path)
            return True

        except Exception as e:
            print(f"Error exporting memo: {e}")
            return False

    def get_total_storage(self) -> int:
        """Calculate total storage used by all memos

        Returns:
            Total size in bytes
        """
        return sum(memo.file_size for memo in self._memos.values())

    def get_memo_count(self) -> int:
        """Get total number of memos

        Returns:
            Number of memos
        """
        return len(self._memos)

    def search_memos(self, query: str) -> List[VoiceMemo]:
        """Search memos by filename

        Args:
            query: Search query

        Returns:
            List of matching VoiceMemo objects
        """
        query_lower = query.lower()
        results = [
            memo
            for memo in self._memos.values()
            if query_lower in memo.filename.lower()
        ]
        results.sort(key=lambda m: m.created_at, reverse=True)
        return results

    def get_storage_directory(self) -> Path:
        """Get storage directory path

        Returns:
            Path to storage directory
        """
        return self.storage_dir
