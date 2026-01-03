from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QInputDialog, QMessageBox

from src.model.codec_config import CodecConfig, CodecPresets
from src.model.format_converter import FormatConverter
from src.model.memo_manager import MemoManager, VoiceMemo
from src.utils.platform_utils import PlatformUtils
from src.view.memo_list_widget import MemoListWidget


class MemoController(QObject):
    """Controller for memo file operations"""

    # Signals
    memo_selected = Signal(object)  # VoiceMemo
    memo_added = Signal(object)  # VoiceMemo
    storage_updated = Signal(int, int)  # num_memos, total_size

    def __init__(
        self,
        memo_manager: MemoManager,
        memo_list_widget: MemoListWidget,
        format_converter: FormatConverter,
        parent: Optional[QObject] = None,
    ):
        """Initialize memo controller

        Args:
            memo_manager: Memo manager model
            memo_list_widget: Memo list widget view
            format_converter: Format converter model
            parent: Parent QObject
        """
        super().__init__(parent)

        self._manager = memo_manager
        self._list_widget = memo_list_widget
        self._converter = format_converter

        self._connect_signals()
        self._refresh_list()

    def _connect_signals(self) -> None:
        """Connect model and view signals"""
        # List widget signals
        self._list_widget.memo_selected.connect(self._on_memo_selected)
        self._list_widget.memo_play_requested.connect(self._on_play_requested)
        self._list_widget.memo_rename_requested.connect(self.rename_memo)
        self._list_widget.memo_convert_requested.connect(self._on_convert_requested)
        self._list_widget.memo_delete_requested.connect(self.delete_memo)
        self._list_widget.memo_open_folder_requested.connect(
            self._on_open_folder_requested
        )

        # Manager signals
        self._manager.memo_added.connect(self._on_memo_added)
        self._manager.memo_removed.connect(self._on_memo_removed)
        self._manager.memo_updated.connect(self._on_memo_updated)

        # Converter signals
        self._converter.conversion_completed.connect(self._on_conversion_completed)

    def refresh_memo_list(self) -> None:
        """Refresh the memo list"""
        self._refresh_list()

    def rename_memo(self, memo_id: str, new_name: str) -> bool:
        """Rename a memo

        Args:
            memo_id: Memo ID
            new_name: New name

        Returns:
            True if successful
        """
        return self._manager.rename_memo(memo_id, new_name)

    def delete_memo(self, memo_id: str) -> bool:
        """Delete a memo with confirmation

        Args:
            memo_id: Memo ID

        Returns:
            True if deleted
        """
        memo = self._manager.get_memo(memo_id)
        if not memo:
            return False

        # Show confirmation dialog
        reply = QMessageBox.question(
            self._list_widget,
            "Delete Memo",
            f"Are you sure you want to delete '{memo.filename}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            return self._manager.delete_memo(memo_id)

        return False

    def convert_memo_format(self, memo_id: str, codec_config: CodecConfig) -> bool:
        """Convert memo to different format

        Args:
            memo_id: Memo ID
            codec_config: Target codec configuration

        Returns:
            True if conversion started
        """
        memo = self._manager.get_memo(memo_id)
        if not memo:
            return False

        input_path = Path(memo.file_path)
        output_path = input_path.with_suffix(codec_config.get_extension())

        # Convert
        return self._converter.convert(
            input_path=input_path, output_path=output_path, codec_config=codec_config
        )

    def import_memo(self, file_path: Path) -> Optional[VoiceMemo]:
        """Import an audio file

        Args:
            file_path: Path to audio file

        Returns:
            Imported VoiceMemo or None
        """
        return self._manager.import_memo(file_path)

    def export_memo(self, memo_id: str, dest_path: Path) -> bool:
        """Export a memo

        Args:
            memo_id: Memo ID
            dest_path: Destination path

        Returns:
            True if successful
        """
        return self._manager.export_memo(memo_id, dest_path)

    def get_selected_memo(self) -> Optional[VoiceMemo]:
        """Get currently selected memo

        Returns:
            Selected VoiceMemo or None
        """
        return self._list_widget.get_selected_memo()

    def add_memo(self, file_path: Path) -> Optional[VoiceMemo]:
        """Add a new memo to the list

        Args:
            file_path: Path to audio file

        Returns:
            Added VoiceMemo or None
        """
        return self._manager.add_memo(file_path)

    def _refresh_list(self) -> None:
        """Refresh memo list in UI"""
        memos = self._manager.list_memos()
        self._list_widget.set_memos(memos)
        self._update_storage_info()

    def _update_storage_info(self) -> None:
        """Update storage information"""
        num_memos = self._manager.get_memo_count()
        total_size = self._manager.get_total_storage()
        self.storage_updated.emit(num_memos, total_size)

    def _on_memo_selected(self, memo: VoiceMemo) -> None:
        """Handle memo selection

        Args:
            memo: Selected VoiceMemo
        """
        self.memo_selected.emit(memo)

    def _on_play_requested(self, memo_id: str) -> None:
        """Handle play request

        Args:
            memo_id: Memo ID
        """
        memo = self._manager.get_memo(memo_id)
        if memo:
            self.memo_selected.emit(memo)

    def _on_convert_requested(self, memo_id: str) -> None:
        """Handle convert request

        Args:
            memo_id: Memo ID
        """
        # Show format selection dialog

        presets = CodecPresets.get_all_presets()
        preset_names = list(presets.keys())

        preset_name, ok = QInputDialog.getItem(
            self._list_widget,
            "Convert Format",
            "Select target format:",
            preset_names,
            0,
            False,
        )

        if ok and preset_name:
            codec_config = presets[preset_name]
            self.convert_memo_format(memo_id, codec_config)

    def _on_open_folder_requested(self, file_path: str) -> None:
        """Handle open folder request

        Args:
            file_path: File path
        """
        path = Path(file_path)
        if path.exists():
            # Open parent directory
            PlatformUtils.open_file_manager(path.parent)

    def _on_memo_added(self, memo: VoiceMemo) -> None:
        """Handle memo added

        Args:
            memo: Added VoiceMemo
        """
        self._refresh_list()
        self.memo_added.emit(memo)

    def _on_memo_removed(self, memo_id: str) -> None:
        """Handle memo removed

        Args:
            memo_id: Removed memo ID
        """
        self._refresh_list()

    def _on_memo_updated(self, memo: VoiceMemo) -> None:
        """Handle memo updated

        Args:
            memo: Updated VoiceMemo
        """
        self._refresh_list()

    def _on_conversion_completed(self, input_path: str, output_path: str) -> None:
        """Handle conversion completed

        Args:
            input_path: Input file path
            output_path: Output file path
        """
        # Add converted file to memo list
        self._manager.scan_directory()
        self._refresh_list()

        # Show notification
        QMessageBox.information(
            self._list_widget,
            "Conversion Complete",
            f"File converted successfully to:\n{Path(output_path).name}",
        )
