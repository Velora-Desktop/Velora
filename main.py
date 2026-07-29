import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from app.ui.main_window import MainWindow
from app.ui.splash_screen import VeloraSplash
from app.storage.startup import prepare_aw02_storage
from app.core.runtime import set_startup_storage
from app.core.constants import APP_VERSION


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Velora")
    app.setApplicationVersion(APP_VERSION)
    splash = VeloraSplash()
    windows = []
    def open_main_window() -> None:
        try:
            storage = prepare_aw02_storage()
            set_startup_storage(storage)
            splash.close(); window = MainWindow(); windows.append(window); window.showMaximized()
            if storage.reset_performed:
                QMessageBox.information(
                    window,
                    "Velora AW0.2",
                    "Профиль безопасно подготовлен для AW0.2.\n"
                    "Исходные данные сохранены в проверенном snapshot и архиве.",
                )
        except Exception as exc:
            splash.close()
            QMessageBox.critical(
                None, "Velora AW0.2 — безопасный запуск",
                "Запуск остановлен, чтобы не повредить локальные данные.\n\n"
                f"{type(exc).__name__}: {exc}",
            )
            app.quit()
    splash.finished.connect(open_main_window)
    splash.start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
