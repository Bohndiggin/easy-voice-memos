from typing import Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMenuBar,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from src.utils.audio_utils import AudioUtils
from src.view.memo_list_widget import MemoListWidget
from src.view.playback_widget import PlaybackWidget
from src.view.recording_panel import RecordingPanel
from src.view.spectrogram_widget import SpectrogramWidget
from src.view.waveform_widget import WaveformWidget


class MainWindow(QMainWindow):
    """Main application window"""

    # Signals
    settings_requested = Signal()
    about_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize main window

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.setWindowTitle("Easy Voice Memos")
        self.setMinimumSize(900, 700)

        # Create UI components
        self.waveform_widget: Optional[WaveformWidget] = None
        self.spectrogram_widget: Optional[SpectrogramWidget] = None
        self.recording_panel: Optional[RecordingPanel] = None
        self.playback_widget: Optional[PlaybackWidget] = None
        self.memo_list_widget: Optional[MemoListWidget] = None

        self._setup_ui()
        self._create_menu_bar()
        self._create_status_bar()

    def _setup_ui(self) -> None:
        """Setup UI components"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Waveform widget
        self.waveform_widget = WaveformWidget()
        self.waveform_widget.setMinimumHeight(150)
        main_layout.addWidget(self.waveform_widget)

        self.spectrogram_widget = SpectrogramWidget()
        self.spectrogram_widget.setMinimumHeight(150)
        main_layout.addWidget(self.spectrogram_widget)

        # Create splitter for panels
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Top panel container (recording + playback)
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # Recording panel
        self.recording_panel = RecordingPanel()
        top_layout.addWidget(self.recording_panel)

        # Playback panel
        self.playback_widget = PlaybackWidget()
        top_layout.addWidget(self.playback_widget)

        splitter.addWidget(top_panel)

        # Memo list widget
        self.memo_list_widget = MemoListWidget()
        splitter.addWidget(self.memo_list_widget)

        # Set initial splitter sizes
        splitter.setSizes([200, 300])

        main_layout.addWidget(splitter)

    def _create_menu_bar(self) -> None:
        """Create menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        # Import action
        import_action = QAction("&Import Audio...", self)
        import_action.setShortcut(QKeySequence.StandardKey.Open)
        file_menu.addAction(import_action)

        file_menu.addSeparator()

        # Settings action
        settings_action = QAction("&Settings...", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self.settings_requested.emit)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        # Quit action
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.quit_requested.emit)
        file_menu.addAction(quit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")

        # Rename action
        rename_action = QAction("&Rename Selected", self)
        rename_action.setShortcut(QKeySequence("F2"))
        edit_menu.addAction(rename_action)

        # Delete action
        delete_action = QAction("&Delete Selected", self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        edit_menu.addAction(delete_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        # Refresh action
        refresh_action = QAction("&Refresh List", self)
        refresh_action.setShortcut(QKeySequence.StandardKey.Refresh)
        view_menu.addAction(refresh_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        # About action
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.about_requested.emit)
        help_menu.addAction(about_action)

    def _create_status_bar(self) -> None:
        """Create status bar"""
        self.statusBar().showMessage("Ready to record")

    def set_status_message(self, message: str) -> None:
        """Set status bar message

        Args:
            message: Status message
        """
        self.statusBar().showMessage(message)

    def update_storage_info(self, num_memos: int, total_size: int) -> None:
        """Update storage information in status bar

        Args:
            num_memos: Number of memos
            total_size: Total size in bytes
        """
        size_str = AudioUtils.format_file_size(total_size)
        message = (
            f"Ready | {num_memos} memo{'s' if num_memos != 1 else ''} | {size_str}"
        )
        self.statusBar().showMessage(message)

    def closeEvent(self, event):
        """Handle window close event"""
        # Save window geometry here if needed
        event.accept()
