from datetime import datetime
from typing import List, Optional

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLineEdit,
    QMenu,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from src.model.memo_manager import VoiceMemo
from src.utils.audio_utils import AudioUtils


class MemoTableModel(QAbstractTableModel):
    """Table model for voice memos"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._memos: List[VoiceMemo] = []
        self._headers = ["Name", "Duration", "Codec", "Sample Rate", "Size", "Date"]

    def rowCount(self, parent=QModelIndex()):
        return len(self._memos)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None

        memo = self._memos[index.row()]
        col = index.column()

        if col == 0:  # Name
            return memo.filename
        elif col == 1:  # Duration
            return AudioUtils.format_duration(memo.duration)
        elif col == 2:  # Codec
            return memo.codec.upper()
        elif col == 3:  # Sample Rate
            return f"{memo.sample_rate // 1000}kHz"
        elif col == 4:  # Size
            return AudioUtils.format_file_size(memo.file_size)
        elif col == 5:  # Date
            # Format date (just the date part)
            dt = datetime.fromisoformat(memo.created_at)
            today = datetime.now().date()
            memo_date = dt.date()

            if memo_date == today:
                return "Today"
            elif (today - memo_date).days == 1:
                return "Yesterday"
            else:
                return dt.strftime("%Y-%m-%d")

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            return self._headers[section]
        return None

    def set_memos(self, memos: List[VoiceMemo]):
        """Update memos list"""
        self.beginResetModel()
        self._memos = memos
        self.endResetModel()

    def get_memo(self, row: int) -> Optional[VoiceMemo]:
        """Get memo at row"""
        if 0 <= row < len(self._memos):
            return self._memos[row]
        return None


class MemoListWidget(QWidget):
    """File browser widget for voice memos"""

    # Signals
    memo_selected = Signal(object)  # VoiceMemo
    memo_play_requested = Signal(str)  # memo_id
    memo_rename_requested = Signal(str, str)  # memo_id, new_name
    memo_convert_requested = Signal(str)  # memo_id
    memo_delete_requested = Signal(str)  # memo_id
    memo_open_folder_requested = Signal(str)  # file_path

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize memo list widget

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._selected_memo: Optional[VoiceMemo] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup UI components"""
        layout = QVBoxLayout(self)

        # Group box
        group = QGroupBox("Voice Memos")
        group_layout = QVBoxLayout()

        # Search bar and controls
        top_layout = QHBoxLayout()

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search memos...")
        self._search_box.textChanged.connect(self._on_search_changed)
        top_layout.addWidget(self._search_box)

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.clicked.connect(self._on_refresh_clicked)
        top_layout.addWidget(self._refresh_btn)

        group_layout.addLayout(top_layout)

        # Table view
        self._table_view = QTableView()
        self._model = MemoTableModel()
        self._table_view.setModel(self._model)

        # Table settings
        self._table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._table_view.setAlternatingRowColors(True)
        self._table_view.setSortingEnabled(True)
        self._table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        # Column widths
        header = self._table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Name
        header.setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )  # Duration
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Codec
        header.setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )  # Sample Rate
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Size
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Date

        # Connect signals
        self._table_view.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )
        self._table_view.doubleClicked.connect(self._on_double_clicked)
        self._table_view.customContextMenuRequested.connect(self._on_context_menu)

        group_layout.addWidget(self._table_view)

        group.setLayout(group_layout)
        layout.addWidget(group)

    def _on_selection_changed(self, selected, deselected) -> None:
        """Handle selection change"""
        indexes = self._table_view.selectedIndexes()
        if indexes:
            row = indexes[0].row()
            memo = self._model.get_memo(row)
            if memo:
                self._selected_memo = memo
                self.memo_selected.emit(memo)

    def _on_double_clicked(self, index: QModelIndex) -> None:
        """Handle double click"""
        memo = self._model.get_memo(index.row())
        if memo:
            self.memo_play_requested.emit(memo.id)

    def _on_context_menu(self, position) -> None:
        """Show context menu"""
        index = self._table_view.indexAt(position)
        if not index.isValid():
            return

        memo = self._model.get_memo(index.row())
        if not memo:
            return

        menu = QMenu(self)

        # Play action
        play_action = QAction("Play", self)
        play_action.triggered.connect(lambda: self.memo_play_requested.emit(memo.id))
        menu.addAction(play_action)

        menu.addSeparator()

        # Rename action
        rename_action = QAction("Rename...", self)
        rename_action.triggered.connect(lambda: self._show_rename_dialog(memo))
        menu.addAction(rename_action)

        # Convert action
        convert_action = QAction("Convert Format...", self)
        convert_action.triggered.connect(
            lambda: self.memo_convert_requested.emit(memo.id)
        )
        menu.addAction(convert_action)

        menu.addSeparator()

        # Show in folder action
        folder_action = QAction("Show in Folder", self)
        folder_action.triggered.connect(
            lambda: self.memo_open_folder_requested.emit(memo.file_path)
        )
        menu.addAction(folder_action)

        menu.addSeparator()

        # Delete action
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(
            lambda: self.memo_delete_requested.emit(memo.id)
        )
        menu.addAction(delete_action)

        menu.exec(self._table_view.viewport().mapToGlobal(position))

    def _show_rename_dialog(self, memo: VoiceMemo) -> None:
        """Show rename dialog"""

        new_name, ok = QInputDialog.getText(
            self, "Rename Memo", "Enter new name:", text=memo.filename
        )

        if ok and new_name and new_name != memo.filename:
            self.memo_rename_requested.emit(memo.id, new_name)

    def _on_search_changed(self, text: str) -> None:
        """Handle search text change"""
        # This would be implemented in the controller
        # For now, just emit a signal or filter locally
        pass

    def _on_refresh_clicked(self) -> None:
        """Handle refresh button click"""
        # Emit signal to controller to refresh
        pass

    def set_memos(self, memos: List[VoiceMemo]) -> None:
        """Update memos list

        Args:
            memos: List of VoiceMemo objects
        """
        self._model.set_memos(memos)

    def get_selected_memo(self) -> Optional[VoiceMemo]:
        """Get currently selected memo

        Returns:
            Selected VoiceMemo or None
        """
        return self._selected_memo

    def clear_selection(self) -> None:
        """Clear table selection"""
        self._table_view.clearSelection()
        self._selected_memo = None
