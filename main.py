from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


def _set_windows_app_id() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Galardo.TradeJournal"
        )
    except Exception:
        pass


def _seed_demo(db) -> None:
    from PySide6.QtCore import QDateTime, QPointF, QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter

    from galardo.widgets import image_to_jpeg

    now = QDateTime.currentDateTime()
    sample_photo = QImage(900, 600, QImage.Format.Format_ARGB32_Premultiplied)
    sample_photo.fill(QColor("#12161C"))
    painter = QPainter(sample_photo)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    gradient = QLinearGradient(QPointF(0, 0), QPointF(900, 600))
    gradient.setColorAt(0.0, QColor("#1B2D4D"))
    gradient.setColorAt(1.0, QColor("#0A0D14"))
    painter.fillRect(QRectF(0, 0, 900, 600), gradient)
    painter.setPen(QColor("#E8EBEF"))
    font = QFont("Segoe UI")
    font.setPixelSize(64)
    font.setWeight(QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(
        QRectF(0, 0, 900, 600),
        Qt.AlignmentFlag.AlignCenter,
        "Truffade\nZ-Type",
    )
    painter.end()

    vivo_id = db.add_deal(
        product="Truffade Vivo",
        side="buy",
        amount=3253525,
        dealt_at=now.addSecs(-3600).toString(Qt.DateFormat.ISODate),
        comment="Взял на перепродажу",
        photo=None,
        created_at=now.toString(Qt.DateFormat.ISODate),
    )
    db.add_deal(
        product="Truffade Vivo",
        side="sell",
        amount=4120000,
        dealt_at=now.addSecs(-600).toString(Qt.DateFormat.ISODate),
        comment="Ушла за полчаса",
        photo=None,
        created_at=now.toString(Qt.DateFormat.ISODate),
        parent_id=vivo_id,
    )
    ztype_id = db.add_deal(
        product="Truffade Z-Type",
        side="buy",
        amount=1080000,
        dealt_at=now.addDays(-1).toString(Qt.DateFormat.ISODate),
        comment="Забрал у продавца",
        photo=None,
        created_at=now.toString(Qt.DateFormat.ISODate),
    )
    db.add_deal(
        product="Truffade Z-Type",
        side="sell",
        amount=1253250,
        dealt_at=now.addSecs(-7200).toString(Qt.DateFormat.ISODate),
        comment="Покупатель забрал в тот же день",
        photo=image_to_jpeg(sample_photo),
        created_at=now.toString(Qt.DateFormat.ISODate),
        parent_id=ztype_id,
    )
    specter_id = db.add_deal(
        product="Dewbauchee Specter",
        side="buy",
        amount=155316,
        dealt_at=now.addDays(-1).toString(Qt.DateFormat.ISODate),
        comment="",
        photo=None,
        created_at=now.toString(Qt.DateFormat.ISODate),
    )
    db.add_deal(
        product="Dewbauchee Specter",
        side="sell",
        amount=172000,
        dealt_at=now.addDays(-1).addSecs(5400).toString(Qt.DateFormat.ISODate),
        comment="",
        photo=None,
        created_at=now.toString(Qt.DateFormat.ISODate),
        parent_id=specter_id,
    )
    db.add_deal(
        product="Куртка Bigness",
        side="buy",
        amount=42000,
        dealt_at=now.addDays(-2).toString(Qt.DateFormat.ISODate),
        comment="Взял пару размеров",
        photo=None,
        created_at=now.toString(Qt.DateFormat.ISODate),
        category="clothing",
    )
    db.add_deal(
        product="Очки «Золото»",
        side="sell",
        amount=68000,
        dealt_at=now.addDays(-9).toString(Qt.DateFormat.ISODate),
        comment="Ушло быстро",
        photo=None,
        created_at=now.toString(Qt.DateFormat.ISODate),
        category="items",
    )


def main() -> int:
    screenshot_path: Path | None = None
    if "--screenshot" in sys.argv:
        index = sys.argv.index("--screenshot")
        value = sys.argv[index + 1] if index + 1 < len(sys.argv) else "screenshot.png"
        screenshot_path = Path(value).resolve()
        if os.environ.get("GALARDO_OFFSCREEN") == "1":
            os.environ["QT_QPA_PLATFORM"] = "offscreen"

    from PySide6.QtCore import QLocale, Qt, QTimer
    from PySide6.QtGui import QFont, QGuiApplication
    from PySide6.QtWidgets import QApplication

    QLocale.setDefault(QLocale(QLocale.Language.Russian, QLocale.Country.Russia))
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    _set_windows_app_id()

    app = QApplication(sys.argv)
    app.setApplicationName("Galardo")
    app.setApplicationDisplayName("Galardo")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))

    from galardo import icons, theme
    from galardo.db import Database
    from galardo.mainwindow import MainWindow

    app.setWindowIcon(icons.app_icon())
    assets = icons.ensure_ui_assets()
    app.setPalette(theme.palette(theme.DEFAULT_THEME, theme.DEFAULT_ACCENT))
    app.setStyleSheet(theme.stylesheet(assets["chevron"]))

    if screenshot_path is not None:
        demo_dir = Path(tempfile.gettempdir()) / "galardo_preview"
        demo_dir.mkdir(parents=True, exist_ok=True)
        db_file = demo_dir / "preview.db"
        if db_file.exists():
            db_file.unlink()
        db = Database(db_file)
        _seed_demo(db)
        window = MainWindow(db)
        window.resize(1180, 760)
        window.show()

        def capture() -> None:
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            window.grab().save(str(screenshot_path), "PNG")
            app.quit()

        QTimer.singleShot(900, capture)
        return app.exec()

    db = Database()
    window = MainWindow(db)
    window.show()
    window.raise_()
    window.activateWindow()
    result = app.exec()
    try:
        db.close()
    except Exception:
        pass
    return result


if __name__ == "__main__":
    raise SystemExit(main())
