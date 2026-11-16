"""Dev helper: renders the main window and popups in both themes to PNG."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QLocale, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication


def main() -> int:
    QLocale.setDefault(QLocale(QLocale.Language.Russian, QLocale.Country.Russia))
    app = QApplication(sys.argv)
    app.setApplicationName("GalardoPreview")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))

    from galardo import icons
    from galardo.db import Database
    from galardo.mainwindow import MainWindow

    app.setWindowIcon(icons.app_icon())

    demo_dir = Path(tempfile.gettempdir()) / "galardo_preview"
    demo_dir.mkdir(parents=True, exist_ok=True)
    db_file = demo_dir / "popup.db"
    if db_file.exists():
        db_file.unlink()
    db = Database(db_file)
    from main import _seed_demo

    _seed_demo(db)
    window = MainWindow(db)
    window.resize(1180, 760)
    window.show()

    def capture_dark() -> None:
        window.grab().save("preview_dark.png", "PNG")
        window._open_settings()
        app.processEvents()

    def capture_settings_dark() -> None:
        window._settings_popup.grab().save("preview_settings_dark.png", "PNG")
        window._settings_popup.close()
        window._on_theme_changed("light")
        app.processEvents()

    def capture_light() -> None:
        window.grab().save("preview_light.png", "PNG")
        window._open_deal_dt_picker()
        app.processEvents()

    def capture_popup_light() -> None:
        window._date_time_popup.grab().save("preview_popup_light.png", "PNG")
        window._date_time_popup.close()
        window._open_settings()
        app.processEvents()

    def capture_settings_light() -> None:
        window._settings_popup.grab().save("preview_settings_light.png", "PNG")
        window._settings_popup.close()
        QTimer.singleShot(150, app.quit)

    QTimer.singleShot(400, capture_dark)
    QTimer.singleShot(750, capture_settings_dark)
    QTimer.singleShot(1150, capture_light)
    QTimer.singleShot(1500, capture_popup_light)
    QTimer.singleShot(1850, capture_settings_light)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
