from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QStyle


class AppStyle:
    """Centralized styling for consistent UI"""

    # Dark Mode Color Scheme
    COLORS = {
        "primary": "#42A5F5",
        "primary_dark": "#1976D2",
        "primary_light": "#64B5F6",
        "accent": "#FF6E40",
        "accent_dark": "#FF3D00",
        "background": "#121212",
        "surface": "#1E1E1E",
        "surface_variant": "#2D2D2D",
        "error": "#CF6679",
        "success": "#66BB6A",
        "text_primary": "#E0E0E0",
        "text_secondary": "#A0A0A0",
        "border": "#3A3A3A",
        "hover": "#2A2A2A",
    }

    @staticmethod
    def get_stylesheet() -> str:
        """Get application-wide QSS stylesheet

        Returns:
            QSS stylesheet string
        """
        return f"""
        /* Main Window */
        QMainWindow {{
            background-color: {AppStyle.COLORS['background']};
        }}

        /* Buttons */
        QPushButton {{
            background-color: {AppStyle.COLORS['primary']};
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-size: 13px;
            min-width: 80px;
        }}

        QPushButton:hover {{
            background-color: {AppStyle.COLORS['primary_dark']};
        }}

        QPushButton:pressed {{
            background-color: {AppStyle.COLORS['primary_dark']};
        }}

        QPushButton:disabled {{
            background-color: {AppStyle.COLORS['border']};
            color: {AppStyle.COLORS['text_secondary']};
        }}

        QPushButton#recordButton {{
            background-color: {AppStyle.COLORS['error']};
            min-width: 100px;
            padding: 10px 20px;
            font-size: 14px;
            font-weight: bold;
        }}

        QPushButton#recordButton:hover {{
            background-color: #D32F2F;
        }}

        QPushButton#stopButton {{
            background-color: {AppStyle.COLORS['text_secondary']};
        }}

        QPushButton#stopButton:hover {{
            background-color: #616161;
        }}

        /* Labels */
        QLabel {{
            color: {AppStyle.COLORS['text_primary']};
            font-size: 13px;
        }}

        QLabel#titleLabel {{
            font-size: 16px;
            font-weight: bold;
            color: {AppStyle.COLORS['text_primary']};
        }}

        QLabel#timerLabel {{
            font-size: 24px;
            font-weight: bold;
            font-family: monospace;
            color: {AppStyle.COLORS['text_primary']};
        }}

        /* GroupBox */
        QGroupBox {{
            background-color: {AppStyle.COLORS['surface']};
            border: 1px solid {AppStyle.COLORS['border']};
            border-radius: 6px;
            margin-top: 12px;
            padding-top: 12px;
            font-weight: bold;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 4px 8px;
            color: {AppStyle.COLORS['text_primary']};
        }}

        /* ComboBox */
        QComboBox {{
            background-color: {AppStyle.COLORS['surface']};
            border: 1px solid {AppStyle.COLORS['border']};
            border-radius: 4px;
            padding: 6px 12px;
            min-width: 150px;
        }}

        QComboBox:hover {{
            border: 1px solid {AppStyle.COLORS['primary']};
        }}

        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}

        QComboBox QAbstractItemView {{
            background-color: {AppStyle.COLORS['surface']};
            border: 1px solid {AppStyle.COLORS['border']};
            selection-background-color: {AppStyle.COLORS['primary']};
            selection-color: {AppStyle.COLORS['text_primary']};
            color: {AppStyle.COLORS['text_primary']};
        }}

        /* Sliders */
        QSlider::groove:horizontal {{
            background: {AppStyle.COLORS['border']};
            height: 4px;
            border-radius: 2px;
        }}

        QSlider::handle:horizontal {{
            background: {AppStyle.COLORS['primary']};
            width: 14px;
            height: 14px;
            margin: -5px 0;
            border-radius: 7px;
        }}

        QSlider::handle:horizontal:hover {{
            background: {AppStyle.COLORS['primary_dark']};
        }}

        QSlider::sub-page:horizontal {{
            background: {AppStyle.COLORS['primary']};
            border-radius: 2px;
        }}

        /* Progress Bar */
        QProgressBar {{
            background-color: {AppStyle.COLORS['border']};
            border: none;
            border-radius: 3px;
            height: 6px;
            text-align: center;
        }}

        QProgressBar::chunk {{
            background-color: {AppStyle.COLORS['primary']};
            border-radius: 3px;
        }}

        /* Table View */
        QTableView {{
            background-color: {AppStyle.COLORS['surface']};
            alternate-background-color: {AppStyle.COLORS['background']};
            border: 1px solid {AppStyle.COLORS['border']};
            border-radius: 4px;
            selection-background-color: {AppStyle.COLORS['primary']};
            selection-color: {AppStyle.COLORS['text_primary']};
            gridline-color: {AppStyle.COLORS['border']};
            color: {AppStyle.COLORS['text_primary']};
        }}

        QTableView::item {{
            padding: 8px;
        }}

        QTableView::item:hover {{
            background-color: {AppStyle.COLORS['hover']};
        }}

        QHeaderView::section {{
            background-color: {AppStyle.COLORS['surface']};
            color: {AppStyle.COLORS['text_primary']};
            padding: 8px;
            border: none;
            border-bottom: 2px solid {AppStyle.COLORS['primary']};
            font-weight: bold;
        }}

        /* Line Edit */
        QLineEdit {{
            background-color: {AppStyle.COLORS['surface']};
            border: 1px solid {AppStyle.COLORS['border']};
            border-radius: 4px;
            padding: 6px 12px;
            selection-background-color: {AppStyle.COLORS['primary']};
            selection-color: {AppStyle.COLORS['text_primary']};
            color: {AppStyle.COLORS['text_primary']};
        }}

        QLineEdit:focus {{
            border: 1px solid {AppStyle.COLORS['primary']};
        }}

        /* Spin Box */
        QSpinBox {{
            background-color: {AppStyle.COLORS['surface']};
            border: 1px solid {AppStyle.COLORS['border']};
            border-radius: 4px;
            padding: 6px 12px;
            color: {AppStyle.COLORS['text_primary']};
        }}

        QSpinBox:focus {{
            border: 1px solid {AppStyle.COLORS['primary']};
        }}

        /* Tab Widget */
        QTabWidget::pane {{
            border: 1px solid {AppStyle.COLORS['border']};
            background-color: {AppStyle.COLORS['surface']};
            border-radius: 4px;
        }}

        QTabBar::tab {{
            background-color: {AppStyle.COLORS['background']};
            border: 1px solid {AppStyle.COLORS['border']};
            border-bottom: none;
            padding: 8px 16px;
            margin-right: 2px;
            color: {AppStyle.COLORS['text_secondary']};
        }}

        QTabBar::tab:selected {{
            background-color: {AppStyle.COLORS['surface']};
            border-bottom: 2px solid {AppStyle.COLORS['primary']};
            color: {AppStyle.COLORS['text_primary']};
        }}

        QTabBar::tab:hover {{
            background-color: {AppStyle.COLORS['hover']};
        }}

        /* Dialog */
        QDialog {{
            background-color: {AppStyle.COLORS['background']};
        }}

        /* Menu Bar */
        QMenuBar {{
            background-color: {AppStyle.COLORS['surface']};
            border-bottom: 1px solid {AppStyle.COLORS['border']};
            color: {AppStyle.COLORS['text_primary']};
        }}

        QMenuBar::item {{
            padding: 6px 12px;
        }}

        QMenuBar::item:selected {{
            background-color: {AppStyle.COLORS['hover']};
        }}

        QMenu {{
            background-color: {AppStyle.COLORS['surface']};
            border: 1px solid {AppStyle.COLORS['border']};
            color: {AppStyle.COLORS['text_primary']};
        }}

        QMenu::item {{
            padding: 6px 24px 6px 12px;
        }}

        QMenu::item:selected {{
            background-color: {AppStyle.COLORS['primary']};
            color: {AppStyle.COLORS['text_primary']};
        }}

        /* Status Bar */
        QStatusBar {{
            background-color: {AppStyle.COLORS['surface']};
            border-top: 1px solid {AppStyle.COLORS['border']};
            color: {AppStyle.COLORS['text_secondary']};
        }}

        /* Text Edit */
        QTextEdit {{
            background-color: {AppStyle.COLORS['surface']};
            border: 1px solid {AppStyle.COLORS['border']};
            border-radius: 4px;
            color: {AppStyle.COLORS['text_primary']};
            selection-background-color: {AppStyle.COLORS['primary']};
            selection-color: {AppStyle.COLORS['text_primary']};
        }}

        /* Check Box */
        QCheckBox {{
            color: {AppStyle.COLORS['text_primary']};
        }}

        /* Radio Button */
        QRadioButton {{
            color: {AppStyle.COLORS['text_primary']};
        }}

        /* Scroll Bar */
        QScrollBar:vertical {{
            background: {AppStyle.COLORS['background']};
            width: 12px;
            border-radius: 6px;
        }}

        QScrollBar::handle:vertical {{
            background: {AppStyle.COLORS['border']};
            border-radius: 6px;
            min-height: 20px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: {AppStyle.COLORS['text_secondary']};
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        """

    @staticmethod
    def get_icon(name: str) -> QIcon:
        """Get standard icon

        Args:
            name: Icon name (e.g., "play", "pause", "record", "stop")

        Returns:
            QIcon object
        """
        # Map custom names to Qt standard icons
        icon_map = {
            "play": QStyle.StandardPixmap.SP_MediaPlay,
            "pause": QStyle.StandardPixmap.SP_MediaPause,
            "stop": QStyle.StandardPixmap.SP_MediaStop,
            "record": QStyle.StandardPixmap.SP_DialogYesButton,
            "folder": QStyle.StandardPixmap.SP_DirIcon,
            "file": QStyle.StandardPixmap.SP_FileIcon,
            "delete": QStyle.StandardPixmap.SP_TrashIcon,
            "settings": QStyle.StandardPixmap.SP_FileDialogDetailedView,
            "save": QStyle.StandardPixmap.SP_DialogSaveButton,
            "open": QStyle.StandardPixmap.SP_DirOpenIcon,
        }

        app = QApplication.instance()
        if app and name in icon_map:
            return app.style().standardIcon(icon_map[name])

        return QIcon()

    @staticmethod
    def get_color(name: str) -> str:
        """Get color by name

        Args:
            name: Color name from COLORS dict

        Returns:
            Hex color string
        """
        return AppStyle.COLORS.get(name, "#000000")
