#!/usr/bin/env python3
"""
Easy Voice Memos - A simple voice memo application with extensive codec support

Main entry point for the application.
"""

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from src.controller.main_controller import MainController
from src.view.main_window import MainWindow
from src.view.style import AppStyle


def main():
    """Main entry point"""
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Easy Voice Memos")
    app.setOrganizationName("VoiceMemos")

    # Set application style
    app.setStyleSheet(AppStyle.get_stylesheet())

    # Enable high DPI support
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    # Create main window
    window = MainWindow()

    # Create main controller
    controller = MainController(window)
    controller.initialize()

    # Show window
    window.show()

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
