from __future__ import annotations

import html
import json
import re
from pathlib import Path

from PySide6.QtCore import (
    QByteArray,
    QBuffer,
    QDate,
    QDateTime,
    QEasingCurve,
    QEvent,
    QIODevice,
    QMimeData,
    QPoint,
    QPropertyAnimation,
    QRectF,
    QSize,
    QTime,
    QTimer,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QDrag,
    QImage,
    QIntValidator,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPalette,
    QPixmap,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QCalendarWidget,
    QColorDialog,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import icons, theme
from .db import Deal

# --------------------------------------------------------------------------- helpers
AMOUNT_PATTERN = r"^\d{0,12}([.,]\d{0,2})?$"
DEAL_DRAG_MIME = "application/x-galardo-deal"


def format_money(value: float, currency: str, with_sign: bool = True) -> str:
    if abs(value) < 0.0001:
        return f"{currency} 0"
    prefix = ""
    if with_sign:
        prefix = "+ " if value > 0 else "- "
    number = abs(value)
    if abs(number - round(number)) < 0.005:
        formatted = f"{int(round(number)):,}".replace(",", " ")
    else:
        formatted = f"{number:,.2f}".replace(",", " ").replace(".", ",")
    return f"{prefix}{currency} {formatted}"


def parse_amount(text: str) -> float | None:
    cleaned = (
        text.strip()
        .replace(" ", "")
        .replace("\u00a0", "")
        .replace("\u202f", "")
        .replace(",", ".")
    )
    if not cleaned:
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return value if value > 0 else None


def deals_word(count: int) -> str:
    count = abs(count) % 100
    last = count % 10
    if 11 <= count <= 14:
        return "сделок"
    if last == 1:
        return "сделка"
    if 2 <= last <= 4:
        return "сделки"
    return "сделок"


def safe_tooltip(text: str) -> str:
    return html.escape(text, quote=True)


def image_to_jpeg(image: QImage, max_side: int = 1600, quality: int = 87) -> bytes:
    if image.isNull():
        return b""
    if max(image.width(), image.height()) > max_side:
        image = image.scaled(
            max_side,
            max_side,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    image = image.convertToFormat(QImage.Format.Format_RGB32)
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "JPEG", quality)
    buffer.close()
    return bytes(data)


def rounded_image_pixmap(
    image: QImage, width: int, height: int, radius: float, dpr: float = 2.0
) -> QPixmap:
    target_w = max(1, int(round(width * dpr)))
    target_h = max(1, int(round(height * dpr)))
    scaled = image.scaled(
        target_w,
        target_h,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    x = max(0, (scaled.width() - target_w) // 2)
    y = max(0, (scaled.height() - target_h) // 2)
    cropped = scaled.copy(x, y, target_w, target_h)

    pixmap = QPixmap(target_w, target_h)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    path = QPainterPath()
    path.addRoundedRect(
        QRectF(0, 0, target_w, target_h), radius * dpr, radius * dpr
    )
    painter.setClipPath(path)
    painter.drawImage(0, 0, cropped)
    painter.end()
    pixmap.setDevicePixelRatio(dpr)
    return pixmap


def make_icon_button(
    name: str,
    tooltip: str,
    color: str | None = None,
    size: int = 15,
) -> QToolButton:
    button = QToolButton()
    button.setObjectName("IconBtn")
    button.setIcon(icons.icon(name, color or theme.icon_tone("muted")))
    button.setIconSize(QSize(size, size))
    button.setFixedSize(25, 25)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setToolTip(tooltip)
    return button


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


# ---------------------------------------------------------------------------- labels
class ElidedLabel(QLabel):
    clicked = Signal()

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._full_text = text
        self._update_pending = False
        self.setTextFormat(Qt.TextFormat.PlainText)
        # ширину задаёт контейнер: длинный текст не должен распирать строку,
        # иначе правый край (цены, кнопки) уезжает за видимую область
        self.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.setMinimumWidth(0)
        self.setToolTip(safe_tooltip(text))
        self.setText(text)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def set_full_text(self, text: str) -> None:
        self._full_text = text
        self.setToolTip(safe_tooltip(text))
        self._schedule_update()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._schedule_update()

    def _schedule_update(self) -> None:
        # setText() меняет sizeHint и снова вызывает resizeEvent. Если делать
        # это прямо из resizeEvent, Qt уходит в рекурсию до переполнения стека
        if self._update_pending:
            return
        self._update_pending = True
        QTimer.singleShot(0, self._safe_update)

    def _safe_update(self) -> None:
        try:
            self._update_text()
        except RuntimeError:
            # виджет уже удалён (список перерисовали до срабатывания таймера)
            pass

    def _update_text(self) -> None:
        self._update_pending = False
        metrics = self.fontMetrics()
        available = max(10, self.width())
        elided = metrics.elidedText(
            self._full_text, Qt.TextElideMode.ElideRight, available
        )
        if elided != self.text():
            self.setText(elided)


class ClickableLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ClickableFrame(QFrame):
    clicked = Signal()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ClickableLineEdit(QLineEdit):
    clicked = Signal()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class TimeEdit(QLineEdit):
    """Small two-digit time input."""

    def __init__(self, maximum: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TimeSpin")
        self.setFixedSize(52, 34)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setPlaceholderText("--")
        self.setMaxLength(2)
        self.setValidator(QIntValidator(0, maximum, self))

    def value(self) -> int:
        text = self.text().strip()
        return int(text) if text.isdigit() else 0

    def set_value(self, value: int) -> None:
        self.setText(f"{max(0, value):02d}")

    def focusInEvent(self, event) -> None:  # noqa: N802
        super().focusInEvent(event)
        QTimer.singleShot(0, self.selectAll)


# ---------------------------------------------------------------------------- popups
def _configure_calendar(calendar: QCalendarWidget) -> None:
    calendar.setGridVisible(False)
    calendar.setVerticalHeaderFormat(
        QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
    )
    calendar.setHorizontalHeaderFormat(
        QCalendarWidget.HorizontalHeaderFormat.ShortDayNames
    )
    calendar.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
    calendar.setMinimumSize(300, 226)

    app = QApplication.instance()
    if app is not None:
        app_palette = app.palette()
        palette = calendar.palette()
        for role in (
            QPalette.ColorRole.Base,
            QPalette.ColorRole.Window,
            QPalette.ColorRole.Text,
            QPalette.ColorRole.WindowText,
            QPalette.ColorRole.Button,
            QPalette.ColorRole.ButtonText,
            QPalette.ColorRole.AlternateBase,
            QPalette.ColorRole.Highlight,
            QPalette.ColorRole.HighlightedText,
        ):
            palette.setColor(role, app_palette.color(role))
        calendar.setPalette(palette)


class PopupBase(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(0)

        self.card = QFrame()
        self.card.setObjectName("PopupCard")
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 170))
        self.card.setGraphicsEffect(shadow)
        outer.addWidget(self.card)

        self.body = QVBoxLayout(self.card)
        self.body.setContentsMargins(12, 12, 12, 12)
        self.body.setSpacing(10)

        QShortcut(QKeySequence(Qt.Key.Key_Escape), self).activated.connect(self.close)

    def show_at(self, anchor: QWidget) -> None:
        self.adjustSize()
        width, height = self.width(), self.height()
        screen = anchor.screen()
        available = screen.availableGeometry() if screen else self.screen().availableGeometry()
        below = anchor.mapToGlobal(QPoint(0, anchor.height() + 6))
        x = min(max(below.x(), available.left() + 8), available.right() - width - 8)
        y = below.y()
        if y + height > available.bottom() - 8:
            y = anchor.mapToGlobal(QPoint(0, -height - 6)).y()
        y = max(available.top() + 8, y)
        self.move(x, y)
        self.show()
        self.raise_()


class DatePopup(PopupBase):
    dateSelected = Signal(QDate)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.calendar = QCalendarWidget()
        _configure_calendar(self.calendar)
        self.calendar.clicked.connect(self._choose)
        self.body.addWidget(self.calendar)

    def _choose(self, date: QDate) -> None:
        self.dateSelected.emit(date)
        self.close()

    def open_for(self, anchor: QWidget, date: QDate) -> None:
        _configure_calendar(self.calendar)
        self.calendar.setSelectedDate(date)
        self.calendar.setCurrentPage(date.year(), date.month())
        self.show_at(anchor)
        self.calendar.setFocus()


class DateTimePopup(PopupBase):
    accepted = Signal(QDateTime)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._date = QDate.currentDate()

        self.calendar = QCalendarWidget()
        _configure_calendar(self.calendar)
        self.calendar.clicked.connect(self._on_date)
        self.body.addWidget(self.calendar)

        time_row = QHBoxLayout()
        time_row.setSpacing(8)
        label = QLabel("Время")
        label.setObjectName("Muted")
        time_row.addWidget(label)

        self.hour_edit = TimeEdit(23)
        time_row.addWidget(self.hour_edit)

        colon = QLabel(":")
        colon.setObjectName("Muted")
        time_row.addWidget(colon)

        self.minute_edit = TimeEdit(59)
        time_row.addWidget(self.minute_edit)

        time_row.addStretch(1)
        self.body.addLayout(time_row)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        now_button = QPushButton("Сейчас")
        now_button.setObjectName("PopupGhost")
        now_button.setCursor(Qt.CursorShape.PointingHandCursor)
        now_button.clicked.connect(self._set_now)
        buttons.addWidget(now_button)
        buttons.addStretch(1)

        cancel_button = QPushButton("Отмена")
        cancel_button.setObjectName("PopupGhost")
        cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_button.clicked.connect(self.close)
        buttons.addWidget(cancel_button)

        done_button = QPushButton("Готово")
        done_button.setObjectName("PopupPrimary")
        done_button.setCursor(Qt.CursorShape.PointingHandCursor)
        done_button.clicked.connect(self._apply)
        buttons.addWidget(done_button)
        self.body.addLayout(buttons)

    def _on_date(self, date: QDate) -> None:
        self._date = date

    def _set_now(self) -> None:
        now = QDateTime.currentDateTime()
        self._date = now.date()
        self.calendar.setSelectedDate(self._date)
        self.calendar.setCurrentPage(self._date.year(), self._date.month())
        self.hour_edit.set_value(now.time().hour())
        self.minute_edit.set_value(now.time().minute())

    def _apply(self) -> None:
        value = QDateTime(
            self._date, QTime(self.hour_edit.value(), self.minute_edit.value())
        )
        self.accepted.emit(value)
        self.close()

    def open_for(self, anchor: QWidget, value: QDateTime) -> None:
        _configure_calendar(self.calendar)
        self._date = value.date()
        self.calendar.setSelectedDate(self._date)
        self.calendar.setCurrentPage(self._date.year(), self._date.month())
        self.hour_edit.set_value(value.time().hour())
        self.minute_edit.set_value(value.time().minute())
        self.show_at(anchor)
        self.calendar.setFocus()


def _color_dot(color: str) -> QPixmap:
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    painter.drawEllipse(QRectF(1.5, 1.5, 13.0, 13.0))
    painter.end()
    return pixmap


def _swatch_style(color: str, selected: bool, theme_name: str) -> str:
    ring = "#1B1F24" if theme_name == "light" else "#F4F5F7"
    hover = "rgba(0, 0, 0, 120)" if theme_name == "light" else "rgba(255, 255, 255, 150)"
    border = f"2px solid {ring}" if selected else "2px solid transparent"
    return (
        "QPushButton {"
        f" background-color: {color};"
        f" border: {border};"
        " border-radius: 13px;"
        " padding: 0px;"
        " min-width: 0px;"
        "}"
        f"QPushButton:hover {{ border-color: {hover}; }}"
    )


class SettingsPopup(PopupBase):
    accentChanged = Signal(str)
    themeChanged = Signal(str)
    photoBackgroundChanged = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._accent = theme.DEFAULT_ACCENT
        self._theme_name = theme.DEFAULT_THEME
        self._photo_bg = True

        title = QLabel("Оформление")
        title.setObjectName("PopupTitle")
        self.body.addWidget(title)

        hint = QLabel("Настройте внешний вид под себя")
        hint.setObjectName("PopupHint")
        self.body.addWidget(hint)

        theme_label = QLabel("Тема")
        theme_label.setObjectName("PopupSection")
        self.body.addWidget(theme_label)

        theme_row = QHBoxLayout()
        theme_row.setSpacing(6)
        self._theme_buttons: dict[str, QPushButton] = {}
        for key, name in theme.THEMES.items():
            button = QPushButton(name)
            button.setObjectName("PopupGhost")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda _checked=False, k=key: self._choose_theme(k)
            )
            self._theme_buttons[key] = button
            theme_row.addWidget(button)
        theme_row.addStretch(1)
        self.body.addLayout(theme_row)

        accent_label = QLabel("Вторичный цвет")
        accent_label.setObjectName("PopupSection")
        self.body.addWidget(accent_label)

        accent_row = QHBoxLayout()
        accent_row.setSpacing(8)
        self._swatches: dict[str, QPushButton] = {}
        for key, (color, name) in theme.ACCENTS.items():
            button = QPushButton()
            button.setFixedSize(26, 26)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(name)
            button.clicked.connect(
                lambda _checked=False, k=key: self._choose_accent(k)
            )
            self._swatches[key] = button
            accent_row.addWidget(button)
        accent_row.addStretch(1)
        self.body.addLayout(accent_row)

        self._custom_button = QPushButton("Свой цвет…")
        self._custom_button.setObjectName("PopupGhost")
        self._custom_button.setCheckable(True)
        self._custom_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._custom_button.setIconSize(QSize(14, 14))
        self._custom_button.setToolTip("Выбрать любой цвет")
        self._custom_button.clicked.connect(self._pick_custom_accent)
        self.body.addWidget(self._custom_button)

        self._photo_button = QPushButton("Фото на фоне")
        self._photo_button.setObjectName("PopupGhost")
        self._photo_button.setCheckable(True)
        self._photo_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._photo_button.setToolTip("Логотип GALARDO за панелями")
        self._photo_button.toggled.connect(self._on_photo_toggled)
        self.body.addWidget(self._photo_button)

    def open_for(
        self,
        anchor: QWidget,
        accent: str,
        theme_name: str,
        photo_bg: bool,
    ) -> None:
        self._accent = accent
        self._theme_name = theme_name if theme_name in theme.THEMES else theme.DEFAULT_THEME
        self._photo_bg = photo_bg
        self.blockSignals(True)
        self._sync()
        self.blockSignals(False)
        self.show_at(anchor)

    def _sync(self) -> None:
        for key, button in self._theme_buttons.items():
            button.setChecked(key == self._theme_name)
        for key, button in self._swatches.items():
            color = theme.ACCENTS[key][0]
            selected = color.lower() == self._accent.lower()
            button.setStyleSheet(
                _swatch_style(color, selected, self._theme_name)
            )
        presets = {color.lower() for color, _ in theme.ACCENTS.values()}
        self._custom_button.setChecked(self._accent.lower() not in presets)
        self._custom_button.setIcon(_color_dot(self._accent))
        self._photo_button.setChecked(self._photo_bg)
        dark = self._theme_name == "dark"
        self._photo_button.setEnabled(dark)
        self._photo_button.setToolTip(
            "Логотип GALARDO за панелями"
            if dark
            else "Фото фона доступно в чёрной теме"
        )

    def _choose_theme(self, key: str) -> None:
        self._theme_name = key
        self._sync()
        self.themeChanged.emit(key)

    def _choose_accent(self, key: str) -> None:
        self._accent = theme.ACCENTS[key][0]
        self._sync()
        self.accentChanged.emit(self._accent)

    def _pick_custom_accent(self) -> None:
        was_visible = self.isVisible()
        position = self.pos()
        color = QColorDialog.getColor(
            QColor(self._accent), self, "Вторичный цвет"
        )
        if color.isValid():
            self._accent = color.name()
            self._sync()
            self.accentChanged.emit(self._accent)
        else:
            self._sync()
        # a modal dialog closes the Qt.Popup window; bring the settings back
        if was_visible:
            self.move(position)
            self.show()
            self.raise_()

    def _on_photo_toggled(self, checked: bool) -> None:
        self._photo_bg = checked
        self.photoBackgroundChanged.emit(checked)


# ----------------------------------------------------------------------------- photo
class PhotoDrop(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PhotoDrop")
        self.setProperty("filled", False)
        self.setFixedHeight(100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAcceptDrops(True)

        self._bytes: bytes | None = None
        self._image: QImage | None = None
        self._file_name = ""

        self._empty_pixmap = icons.icon_pixmap(
            "photo", theme.icon_tone("text"), 96
        ).scaled(
            52,
            52,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._empty_pixmap.setDevicePixelRatio(2.0)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 12, 12)
        layout.setSpacing(13)

        self._preview = QLabel()
        self._preview.setObjectName("PhotoIcon")
        self._preview.setFixedSize(54, 54)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setPixmap(self._empty_pixmap)
        layout.addWidget(self._preview)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)
        self._title = QLabel("Вставьте фото из буфера обмена")
        self._title.setObjectName("PhotoTitle")
        self._title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._hint = QLabel("Ctrl+V или нажмите, чтобы выбрать файл")
        self._hint.setObjectName("PhotoHint")
        self._hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._hint.setWordWrap(True)
        text_layout.addWidget(self._title)
        text_layout.addWidget(self._hint)
        layout.addLayout(text_layout, 1)

        self._clear = QToolButton()
        self._clear.setObjectName("IconBtn")
        self._clear.setIcon(icons.icon("close", theme.icon_tone("muted")))
        self._clear.setIconSize(QSize(12, 12))
        self._clear.setFixedSize(24, 24)
        self._clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear.setToolTip("Убрать фото")
        self._clear.clicked.connect(self.clear)
        self._clear.hide()
        layout.addWidget(self._clear, 0, Qt.AlignmentFlag.AlignTop)

    # ------------------------------------------------------------------ public
    def photo_bytes(self) -> bytes | None:
        return self._bytes

    def has_photo(self) -> bool:
        return bool(self._bytes)

    def paste_from_clipboard(self) -> bool:
        clipboard = QApplication.clipboard()
        image = clipboard.image()
        if not image.isNull():
            self.set_image(image)
            return True
        mime = clipboard.mimeData()
        if mime is not None:
            for url in mime.urls():
                path = url.toLocalFile()
                if path and self._looks_like_image(path):
                    file_image = QImage(path)
                    if not file_image.isNull():
                        self.set_image(file_image, Path(path).name)
                        return True
        return False

    def set_image(self, image: QImage, file_name: str = "") -> None:
        if image.isNull():
            return
        self._image = image
        self._bytes = image_to_jpeg(image)
        self._file_name = file_name
        self._update_view()

    def set_bytes(self, data: bytes | None, file_name: str = "") -> None:
        if not data:
            self.clear()
            return
        image = QImage.fromData(data)
        if image.isNull():
            self.clear()
            return
        self._bytes = bytes(data)
        self._image = image
        self._file_name = file_name
        self._update_view()

    def clear(self) -> None:
        self._bytes = None
        self._image = None
        self._file_name = ""
        self.setProperty("filled", False)
        repolish(self)
        self._preview.setPixmap(self._empty_pixmap)
        self._title.setText("Вставьте фото из буфера обмена")
        self._hint.setText("Ctrl+V или нажмите, чтобы выбрать файл")
        self._hint.setToolTip("")
        self._clear.hide()

    def refresh_icons(self) -> None:
        self._empty_pixmap = icons.icon_pixmap(
            "photo", theme.icon_tone("text"), 96
        ).scaled(
            52,
            52,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._empty_pixmap.setDevicePixelRatio(2.0)
        self._clear.setIcon(icons.icon("close", theme.icon_tone("muted")))
        if not self.has_photo():
            self._preview.setPixmap(self._empty_pixmap)

    # ------------------------------------------------------------------ events
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._pick()
        super().mousePressEvent(event)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        mime = event.mimeData()
        if mime.hasImage():
            event.acceptProposedAction()
            return
        if mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile() and self._looks_like_image(url.toLocalFile()):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        mime = event.mimeData()
        if mime.hasImage():
            image = QImage(mime.imageData())
            if not image.isNull():
                self.set_image(image)
                event.acceptProposedAction()
                return
        for url in mime.urls():
            path = url.toLocalFile()
            if path and self._looks_like_image(path):
                image = QImage(path)
                if not image.isNull():
                    self.set_image(image, Path(path).name)
                    event.acceptProposedAction()
                    return
        event.ignore()

    # ----------------------------------------------------------------- internal
    def _pick(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбрать фото сделки",
            "",
            "Изображения (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff)",
        )
        if not path:
            return
        image = QImage(path)
        if image.isNull():
            QMessageBox.warning(self, "Фото", "Не удалось открыть это изображение.")
            return
        self.set_image(image, Path(path).name)

    def _update_view(self) -> None:
        if self._image is None:
            self.clear()
            return
        self.setProperty("filled", True)
        repolish(self)
        self._preview.setPixmap(
            rounded_image_pixmap(self._image, 54, 54, 10.0)
        )
        self._title.setText("Фото прикреплено")
        hint = self._file_name or "Нажмите, чтобы заменить · Ctrl+V"
        self._hint.setText(hint)
        self._hint.setToolTip(safe_tooltip(self._file_name) if self._file_name else "")
        self._clear.show()

    @staticmethod
    def _looks_like_image(path: str) -> bool:
        return Path(path).suffix.lower() in {
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".bmp",
            ".gif",
            ".tif",
            ".tiff",
        }


# -------------------------------------------------------------------------- deal card
class DragHandle(QLabel):
    """Точка захвата: тянет карточку или всю пару «покупка + продажа»."""

    def __init__(
        self,
        deal_ids: list[int],
        week: int,
        source: QWidget,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._ids = list(deal_ids)
        self._week = week
        self._source = source
        self._press: QPoint | None = None
        self.setObjectName("DragHandle")
        self.setFixedSize(16, 24)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip("Перетащить выше или ниже")

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._press = event.position().toPoint()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._press is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            return super().mouseMoveEvent(event)
        distance = (event.position().toPoint() - self._press).manhattanLength()
        if distance < QApplication.startDragDistance():
            return

        self._press = None
        payload = json.dumps({"ids": self._ids, "week": self._week})
        mime = QMimeData()
        mime.setData(DEAL_DRAG_MIME, QByteArray(payload.encode("utf-8")))

        drag = QDrag(self)
        drag.setMimeData(mime)
        pixmap = self._source.grab()
        if pixmap.width() > 420:
            pixmap = pixmap.scaledToWidth(
                420, Qt.TransformationMode.SmoothTransformation
            )
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(14, min(20, pixmap.height() // 2)))
        self.window().setCursor(Qt.CursorShape.ClosedHandCursor)
        drag.exec(Qt.DropAction.MoveAction)
        self.window().unsetCursor()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(theme.icon_tone("muted")))
        radius = 1.4
        for row in range(3):
            for column in range(2):
                x = self.width() / 2 + (column - 0.5) * 6
                y = self.height() / 2 + (row - 1) * 6
                painter.drawEllipse(QRectF(x - radius, y - radius, radius * 2, radius * 2))


class DealCard(QFrame):
    editRequested = Signal(int)
    deleteRequested = Signal(int)
    quickRequested = Signal(int, str)
    photoRequested = Signal(int)
    statsRequested = Signal(int)

    def __init__(self, deal: Deal, currency: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.deal = deal
        self.setObjectName("DealCard")
        self.setProperty("side", deal.side)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self._drag_handle: DragHandle | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(6)
        self._header_layout = header
        title = ElidedLabel(deal.product)
        title.setObjectName("DealTitle")
        title.setMinimumWidth(80)
        title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        title.setCursor(Qt.CursorShape.PointingHandCursor)
        title.setToolTip(
            safe_tooltip(f"{deal.product} · статистика за 30 дней")
        )
        title.clicked.connect(lambda: self.statsRequested.emit(deal.id))
        header.addWidget(title, 1)

        edit_button = make_icon_button("pencil", "Редактировать сделку")
        edit_button.clicked.connect(lambda: self.editRequested.emit(deal.id))
        header.addWidget(edit_button)
        self._edit_button = edit_button

        delete_button = make_icon_button("trash", "Удалить сделку")
        delete_button.clicked.connect(lambda: self.deleteRequested.emit(deal.id))
        header.addWidget(delete_button)
        self._delete_button = delete_button
        layout.addLayout(header)

        meta = QHBoxLayout()
        meta.setSpacing(8)
        badge = QLabel("Купил" if deal.side == "buy" else "Продал")
        badge.setObjectName("BadgeBuy" if deal.side == "buy" else "BadgeSell")
        meta.addWidget(badge)

        amount = QLabel(format_money(deal.signed_amount, currency))
        amount.setObjectName("AmountBuy" if deal.side == "buy" else "AmountSell")
        meta.addWidget(amount)
        meta.addStretch(1)

        date = QDateTime.fromString(deal.dealt_at, Qt.DateFormat.ISODate)
        date_text = date.toString("dd.MM.yy HH:mm") if date.isValid() else deal.dealt_at
        date_label = QLabel(date_text)
        date_label.setObjectName("DealDate")
        meta.addWidget(date_label, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(meta)

        actions = QHBoxLayout()
        actions.setSpacing(7)
        sell_same = QPushButton("Продал такое")
        sell_same.setObjectName("Chip")
        sell_same.setCursor(Qt.CursorShape.PointingHandCursor)
        sell_same.clicked.connect(lambda: self.quickRequested.emit(deal.id, "sell"))
        actions.addWidget(sell_same)

        buy_same = QPushButton("Купил такое")
        buy_same.setObjectName("Chip")
        buy_same.setCursor(Qt.CursorShape.PointingHandCursor)
        buy_same.clicked.connect(lambda: self.quickRequested.emit(deal.id, "buy"))
        actions.addWidget(buy_same)
        actions.addStretch(1)

        if deal.photo:
            image = QImage.fromData(deal.photo)
            if not image.isNull():
                thumb = ClickableLabel()
                thumb.setFixedSize(40, 40)
                thumb.setCursor(Qt.CursorShape.PointingHandCursor)
                thumb.setToolTip("Открыть фото")
                thumb.setPixmap(rounded_image_pixmap(image, 40, 40, 8.0))
                thumb.clicked.connect(lambda: self.photoRequested.emit(deal.id))
                actions.addWidget(thumb, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(actions)

        if deal.comment:
            comment = QLabel(deal.comment)
            comment.setObjectName("DealComment")
            comment.setTextFormat(Qt.TextFormat.PlainText)
            comment.setWordWrap(True)
            comment.setToolTip(safe_tooltip(deal.comment))
            layout.addWidget(comment)

    def enable_drag(self, deal_ids: list[int], week: int) -> None:
        if self._drag_handle is not None:
            return
        self._drag_handle = DragHandle(deal_ids, week, self)
        self._header_layout.insertWidget(0, self._drag_handle)

    def refresh_icons(self) -> None:
        tone = theme.icon_tone("muted")
        self._edit_button.setIcon(icons.icon("pencil", tone))
        self._delete_button.setIcon(icons.icon("trash", tone))
        if self._drag_handle is not None:
            self._drag_handle.update()


# ------------------------------------------------------------------------- week group
class WeekSection(QWidget):
    toggled = Signal(bool)
    dealDropped = Signal(object, int)

    def __init__(
        self,
        number: int,
        start: QDate,
        end: QDate,
        count: int,
        total: float,
        currency: str,
        expanded: bool,
        week: int = 0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._expanded = expanded
        self._week = week
        self._drop_ids: list[int] | None = None
        self._drop_index = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(7)

        self._header = ClickableFrame()
        self._header.setObjectName("WeekHeader")
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        header = QHBoxLayout(self._header)
        header.setContentsMargins(10, 7, 12, 7)
        header.setSpacing(8)

        self._chevron = QLabel("▾" if expanded else "▸")
        self._chevron.setObjectName("WeekChevron")
        self._chevron.setFixedWidth(12)
        header.addWidget(self._chevron)

        title = QLabel(
            f"Неделя {number} · {start.toString('dd.MM')} – {end.toString('dd.MM')}"
        )
        title.setObjectName("WeekTitle")
        header.addWidget(title)
        header.addStretch(1)

        meta = QLabel(f"{count} {deals_word(count)}")
        meta.setObjectName("WeekMeta")
        header.addWidget(meta)

        amount = QLabel(format_money(total, currency))
        amount.setObjectName("WeekAmount")
        header.addWidget(amount)
        outer.addWidget(self._header)

        self.body = QWidget()
        self.body.setObjectName("WeekBody")
        self.body.setAcceptDrops(True)
        self.body.installEventFilter(self)
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(9)
        self.body.setVisible(expanded)
        outer.addWidget(self.body)

        self._drop_line = QFrame(self.body)
        self._drop_line.setObjectName("DropLine")
        self._drop_line.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        self._drop_line.setFixedHeight(2)
        self._drop_line.hide()

        self._header.clicked.connect(self._toggle)

    def add_card(self, card: QWidget) -> None:
        self.body_layout.addWidget(card)

    def refresh_icons(self) -> None:
        for index in range(self.body_layout.count()):
            item = self.body_layout.itemAt(index)
            widget = item.widget() if item is not None else None
            if isinstance(widget, (DealCard, PairSection)):
                widget.refresh_icons()

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        self.body.setVisible(self._expanded)
        self._chevron.setText("▾" if self._expanded else "▸")
        self.toggled.emit(self._expanded)

    # ------------------------------------------------------------- drag & drop
    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self.body:
            kind = event.type()
            if kind in (
                QEvent.Type.DragEnter,
                QEvent.Type.DragMove,
            ):
                payload = self._drag_payload(event.mimeData())
                if payload is None:
                    event.ignore()
                    return True
                self._drop_ids = payload["ids"]
                self._drop_index, line_y = self._drop_position(
                    event.position().toPoint()
                )
                self._show_drop_line(line_y)
                event.acceptProposedAction()
                return True
            if kind == QEvent.Type.DragLeave:
                self._hide_drop_line()
                event.accept()
                return True
            if kind == QEvent.Type.Drop:
                payload = self._drag_payload(event.mimeData())
                self._hide_drop_line()
                if payload is None:
                    event.ignore()
                    return True
                self.dealDropped.emit(payload["ids"], self._drop_index)
                event.acceptProposedAction()
                return True
        return super().eventFilter(obj, event)

    def _drag_payload(self, mime) -> dict | None:
        if mime is None or not mime.hasFormat(DEAL_DRAG_MIME):
            return None
        try:
            payload = json.loads(
                bytes(mime.data(DEAL_DRAG_MIME)).decode("utf-8")
            )
        except (ValueError, UnicodeDecodeError):
            return None
        if not isinstance(payload, dict):
            return None
        if payload.get("week") != self._week:
            return None
        ids = payload.get("ids")
        if not isinstance(ids, list) or not ids:
            return None
        return {"ids": [int(value) for value in ids]}

    def _drop_position(self, pos: QPoint) -> tuple[int, int]:
        """Индекс вставки и Y линии-подсказки (с учётом перетаскиваемого)."""
        widgets: list[QWidget] = []
        for index in range(self.body_layout.count()):
            item = self.body_layout.itemAt(index)
            widget = item.widget() if item is not None else None
            if widget is not None and widget is not self._drop_line:
                widgets.append(widget)
        source = None
        for widget in widgets:
            if getattr(widget, "entry_ids", None) == self._drop_ids:
                source = widget
                break
        others = [widget for widget in widgets if widget is not source]
        if not others:
            return 0, 0

        index = 0
        for widget in others:
            if pos.y() < widget.geometry().center().y():
                break
            index += 1
        if index == 0:
            y = others[0].geometry().top()
        elif index == len(others):
            y = others[-1].geometry().bottom() + 1
        else:
            y = (others[index - 1].geometry().bottom() + others[index].geometry().top()) // 2
        y = max(0, min(y, max(0, self.body.height() - 2)))
        return index, y

    def _show_drop_line(self, y: int) -> None:
        self._drop_line.setGeometry(0, y, max(0, self.body.width()), 2)
        self._drop_line.show()
        self._drop_line.raise_()

    def _hide_drop_line(self) -> None:
        self._drop_line.hide()
        self._drop_ids = None


# ------------------------------------------------------------------------- pair group
class PairSection(QWidget):
    """Свёрнутая пара «покупка + продажа» одного предмета."""

    toggled = Signal(bool)
    statsRequested = Signal(int)

    def __init__(
        self,
        deal: Deal,
        children: list[Deal],
        currency: str,
        expanded: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._expanded = expanded
        self._drag_handle: DragHandle | None = None
        self._header_layout: QHBoxLayout | None = None
        members = [deal] + list(children)
        total = sum(item.signed_amount for item in members)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(7)

        self._header = ClickableFrame()
        self._header.setObjectName("PairHeader")
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        header = QHBoxLayout(self._header)
        header.setContentsMargins(9, 7, 12, 7)
        header.setSpacing(8)
        self._header_layout = header

        self._chevron = QLabel("▾" if expanded else "▸")
        self._chevron.setObjectName("PairChevron")
        self._chevron.setFixedWidth(12)
        header.addWidget(self._chevron)

        title = ElidedLabel(deal.product)
        title.setObjectName("PairTitle")
        title.setMinimumWidth(80)
        title.setCursor(Qt.CursorShape.PointingHandCursor)
        title.setToolTip(
            safe_tooltip(f"{deal.product} · статистика за 30 дней")
        )
        title.clicked.connect(lambda: self.statsRequested.emit(deal.id))
        header.addWidget(title, 1)

        if len(children) == 1:
            meta_text = (
                f"Купил {format_money(deal.amount, currency, with_sign=False)}"
                f" · Продал "
                f"{format_money(children[0].amount, currency, with_sign=False)}"
            )
        else:
            meta_text = f"Покупка и {len(children)} {_sales_word(len(children))}"
        meta = QLabel(meta_text)
        meta.setObjectName("PairMeta")
        header.addWidget(meta)

        profit = QLabel(format_money(total, currency))
        profit.setObjectName("PairProfit")
        profit.setProperty(
            "state", "positive" if total > 0.004 else "negative" if total < -0.004 else ""
        )
        header.addWidget(profit)
        outer.addWidget(self._header)

        self.body = QWidget()
        self.body.setObjectName("PairBody")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(20, 0, 0, 0)
        self.body_layout.setSpacing(7)
        self.body.setVisible(expanded)
        outer.addWidget(self.body)

        self._header.clicked.connect(self._toggle)

    def add_card(self, card: QWidget) -> None:
        self.body_layout.addWidget(card)

    def enable_drag(self, deal_ids: list[int], week: int) -> None:
        if self._drag_handle is not None or self._header_layout is None:
            return
        self._drag_handle = DragHandle(deal_ids, week, self._header)
        self._header_layout.insertWidget(1, self._drag_handle)

    def refresh_icons(self) -> None:
        for index in range(self.body_layout.count()):
            item = self.body_layout.itemAt(index)
            widget = item.widget() if item is not None else None
            if isinstance(widget, DealCard):
                widget.refresh_icons()
        if self._drag_handle is not None:
            self._drag_handle.update()

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        self.body.setVisible(self._expanded)
        self._chevron.setText("▾" if self._expanded else "▸")
        self.toggled.emit(self._expanded)


def _sales_word(count: int) -> str:
    count = abs(count) % 100
    last = count % 10
    if 11 <= count <= 14:
        return "продаж"
    if last == 1:
        return "продажа"
    if 2 <= last <= 4:
        return "продажи"
    return "продаж"


# ------------------------------------------------------------------------- title bar
class TitleBar(QWidget):
    minimizeRequested = Signal()
    maximizeRequested = Signal()
    closeRequested = Signal()
    settingsRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(54)
        self._drag_offset: QPoint | None = None
        self._is_maximized = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 0, 10, 0)
        layout.setSpacing(10)

        logo = QLabel()
        logo.setPixmap(icons.logo_pixmap(26))
        logo.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(logo)

        title = QLabel("Galardo")
        title.setObjectName("AppTitle")
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(title)
        layout.addStretch(1)

        self.settings_button = QToolButton()
        self.settings_button.setObjectName("WinBtn")
        self.settings_button.setIcon(icons.icon("gear", theme.icon_tone("strong")))
        self.settings_button.setIconSize(QSize(15, 15))
        self.settings_button.setFixedSize(32, 28)
        self.settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_button.setToolTip("Оформление")
        self.settings_button.clicked.connect(self.settingsRequested.emit)
        layout.addWidget(self.settings_button, 0, Qt.AlignmentFlag.AlignVCenter)

        self._minimize = QToolButton()
        self._minimize.setObjectName("WinBtn")
        self._minimize.setIcon(icons.icon("minus", theme.icon_tone("strong")))
        self._minimize.setIconSize(QSize(12, 12))
        self._minimize.setFixedSize(34, 28)
        self._minimize.setCursor(Qt.CursorShape.PointingHandCursor)
        self._minimize.setToolTip("Свернуть")
        self._minimize.clicked.connect(self.minimizeRequested.emit)
        layout.addWidget(self._minimize, 0, Qt.AlignmentFlag.AlignVCenter)

        self._maximize = QToolButton()
        self._maximize.setObjectName("WinBtn")
        self._maximize.setIcon(icons.icon("maximize", theme.icon_tone("strong")))
        self._maximize.setIconSize(QSize(12, 12))
        self._maximize.setFixedSize(34, 28)
        self._maximize.setCursor(Qt.CursorShape.PointingHandCursor)
        self._maximize.setToolTip("Развернуть")
        self._maximize.clicked.connect(self.maximizeRequested.emit)
        layout.addWidget(self._maximize, 0, Qt.AlignmentFlag.AlignVCenter)

        self._close = QToolButton()
        self._close.setObjectName("WinClose")
        self._close.setIcon(icons.icon("close", theme.icon_tone("strong")))
        self._close.setIconSize(QSize(12, 12))
        self._close.setFixedSize(34, 28)
        self._close.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close.setToolTip("Закрыть")
        self._close.clicked.connect(self.closeRequested.emit)
        layout.addWidget(self._close, 0, Qt.AlignmentFlag.AlignVCenter)

    def refresh_icons(self) -> None:
        tone = theme.icon_tone("strong")
        self.settings_button.setIcon(icons.icon("gear", tone))
        self._minimize.setIcon(icons.icon("minus", tone))
        self._maximize.setIcon(
            icons.icon("restore" if self._is_maximized else "maximize", tone)
        )
        self._close.setIcon(icons.icon("close", tone))

    def set_maximized(self, maximized: bool) -> None:
        self._is_maximized = maximized
        self._maximize.setToolTip("Восстановить" if maximized else "Развернуть")
        self._maximize.setIcon(
            icons.icon(
                "restore" if maximized else "maximize", theme.icon_tone("strong")
            )
        )

    # dragging / double click maximise
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and not self.window().isMaximized():
            self._drag_offset = (
                event.globalPosition().toPoint()
                - self.window().frameGeometry().topLeft()
            )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if (
            self._drag_offset is not None
            and event.buttons() & Qt.MouseButton.LeftButton
            and not self.window().isMaximized()
        ):
            self.window().move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximizeRequested.emit()
        super().mouseDoubleClickEvent(event)


# ----------------------------------------------------------------------------- toast
class ResizeGrip(QWidget):
    """Small visible corner handle for the frameless window."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setToolTip("Изменить размер окна")
        self._start_global: QPoint | None = None
        self._start_size: QSize | None = None

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 52))
        for x, y in ((13, 13), (13, 9), (9, 13)):
            painter.drawRect(x, y, 2, 2)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_global = event.globalPosition().toPoint()
            self._start_size = self.window().size()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if (
            self._start_global is not None
            and self._start_size is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            delta = event.globalPosition().toPoint() - self._start_global
            window = self.window()
            width = max(window.minimumWidth(), self._start_size.width() + delta.x())
            height = max(window.minimumHeight(), self._start_size.height() + delta.y())
            window.resize(width, height)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._start_global = None
        self._start_size = None
        super().mouseReleaseEvent(event)


class Toast(QLabel):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hide()

        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(0.0)
        self.setGraphicsEffect(self._effect)

        self._animation = QPropertyAnimation(self._effect, b"opacity", self)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._animation.finished.connect(self._on_animation_finished)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)

    def show_message(self, text: str) -> None:
        self.setText(text)
        self.adjustSize()
        self._reposition()
        self._effect.setOpacity(0.0)
        self.show()
        self.raise_()
        self._animation.stop()
        self._animation.setDuration(160)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.start()
        self._timer.start(1900)

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if not parent:
            return
        width = min(self.width(), parent.width() - 48)
        if width != self.width():
            self.setFixedWidth(width)
        x = max(20, (parent.width() - self.width()) // 2)
        y = parent.height() - self.height() - 34
        self.move(x, y)

    def _fade_out(self) -> None:
        self._animation.stop()
        self._animation.setDuration(380)
        self._animation.setStartValue(self._effect.opacity())
        self._animation.setEndValue(0.0)
        self._animation.start()

    def _on_animation_finished(self) -> None:
        if self._effect.opacity() <= 0.04:
            self.hide()


# ---------------------------------------------------------------------- image overlay
class ImageOverlay(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("ImageOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.hide()

        self._image = QImage()

        self._title = QLabel(self)
        self._title.setObjectName("OverlayTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._picture = QLabel(self)
        self._picture.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._picture.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._hint = QLabel("Нажмите в любом месте, чтобы закрыть", self)
        self._hint.setObjectName("OverlayHint")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._close = QToolButton(self)
        self._close.setObjectName("OverlayClose")
        self._close.setIcon(icons.icon("close", "#E7E9EC"))
        self._close.setIconSize(QSize(14, 14))
        self._close.setFixedSize(34, 34)
        self._close.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close.setToolTip("Закрыть")
        self._close.clicked.connect(self.hide)

    def show_image(self, data: bytes, product: str) -> None:
        image = QImage.fromData(data)
        if image.isNull():
            return
        self.show_qimage(image, product)

    def show_qimage(self, image: QImage, product: str) -> None:
        if image.isNull():
            return
        self._image = image
        self._title.setText(product)
        self.setGeometry(self.parentWidget().rect())
        self._update_content()
        self.show()
        self.raise_()
        self.setFocus()

    def _update_content(self) -> None:
        if self._image.isNull():
            return
        margin = 80
        max_width = max(100, self.width() - margin * 2)
        max_height = max(100, self.height() - margin * 2 - 30)
        pixmap = QPixmap.fromImage(self._image)
        if pixmap.width() > max_width or pixmap.height() > max_height:
            pixmap = pixmap.scaled(
                max_width,
                max_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self._picture.setPixmap(pixmap)
        x = (self.width() - pixmap.width()) // 2
        y = (self.height() - pixmap.height()) // 2
        self._picture.setGeometry(x, y, pixmap.width(), pixmap.height())
        self._title.setGeometry(30, 22, max(100, self.width() - 60), 24)
        self._hint.setGeometry(30, self.height() - 42, max(100, self.width() - 60), 20)
        self._close.move(self.width() - 34 - 22, 20)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_content()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.hide()
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            return
        super().keyPressEvent(event)
