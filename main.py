import sys

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.splash_screen import VeloraSplash


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Velora")
    app.setApplicationVersion("AW0.05")
    splash = VeloraSplash()
    windows = []
    def open_main_window() -> None:
        splash.close(); window = MainWindow(); windows.append(window); window.showMaximized()
    splash.finished.connect(open_main_window)
    splash.start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
