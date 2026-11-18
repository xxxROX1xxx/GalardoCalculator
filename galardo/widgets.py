from __future__ import annotations

import html
import json
import re
from collections.abc import Callable
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
    QObject,
    QPoint,
    QPropertyAnimation,
    QRectF,
    QSize,
    QTime,
    QTimer,
    Qt,
    QVariantAnimation,
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
    QAbstractButton,
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
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import design, icons, theme, ui_kit
from .db import CATEGORIES, Deal

# --------------------------------------------------------------------------- helpers
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
    )
    if not cleaned:
        return None
    if "," in cleaned:
        # запятая — дробная часть, точки — разделители тысяч
        whole, _, fraction = cleaned.partition(",")
        cleaned = f"{whole.replace('.', '') or '0'}.{fraction or '0'}"
    else:
        cleaned = cleaned.replace(".", "")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return value if value > 0 else None


def format_amount_text(text: str) -> str:
    """Разделить тысячи точками: 1000000 -> 1.000.000, 1234,5 -> 1.234,5."""
    cleaned = (
        text.strip()
        .replace(" ", "")
        .replace("\u00a0", "")
        .replace("\u202f", "")
    )
    if not cleaned:
        return ""
    whole, comma, fraction = cleaned.partition(",")
    digits = "".join(char for char in whole if char.isdigit())[:12]
    rest = "".join(char for char in fraction if char.isdigit())[:2]
    grouped = f"{int(digits):,}".replace(",", ".") if digits else ""
    if comma or rest:
        return f"{grouped or '0'},{rest}"
    return grouped


class AmountLineEdit(QLineEdit):
    """Поле суммы: точки разделяют тысячи, запятая — копейки."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._formatting = False
        self.textEdited.connect(self._reformat)

    def setText(self, text: str) -> None:  # noqa: N802
        super().setText(format_amount_text(text))

    def _reformat(self, text: str) -> None:
        if self._formatting:
            return
        formatted = format_amount_text(text)
        if formatted == text:
            return
        digits = sum(
            1 for char in text[: self.cursorPosition()] if char.isdigit()
        )
        self._formatting = True
        super().setText(formatted)
        self._formatting = False
        self._move_caret(digits)

    def _move_caret(self, digits: int) -> None:
        if digits <= 0:
            self.setCursorPosition(0)
            return
        seen = 0
        for index, char in enumerate(self.text()):
            if char.isdigit():
                seen += 1
                if seen == digits:
                    self.setCursorPosition(index + 1)
                    return
        self.setCursorPosition(len(self.text()))


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
    image: QImage,
    width: int,
    height: int,
    radius: float,
    dpr: float = 2.0,
    fit: bool = True,
) -> QPixmap:
    """Rounded thumbnail that keeps the whole photo visible by default.

    ``fit=True`` scales the image down to the box (letterboxed bands stay
    transparent, so the label background shows through). ``fit=False`` keeps
    the old cover behaviour for callers that explicitly want a crop.
    """
    target_w = max(1, int(round(width * dpr)))
    target_h = max(1, int(round(height * dpr)))

    pixmap = QPixmap(target_w, target_h)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    path = QPainterPath()
    path.addRoundedRect(
        QRectF(0, 0, target_w, target_h), radius * dpr, radius * dpr
    )
    painter.setClipPath(path)
    if fit:
        scaled = image.scaled(
            target_w,
            target_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (target_w - scaled.width()) // 2
        y = (target_h - scaled.height()) // 2
        painter.drawImage(x, y, scaled)
    else:
        scaled = image.scaled(
            target_w,
            target_h,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = max(0, (scaled.width() - target_w) // 2)
        y = max(0, (scaled.height() - target_h) // 2)
        painter.drawImage(0, 0, scaled.copy(x, y, target_w, target_h))
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


# ------------------------------------------------------------------------- animations
def fade_in(widget: QWidget, duration: int = 170) -> None:
    """Fade a freshly switched page in without leaving a permanent effect."""
    previous = getattr(widget, "_fade_animation", None)
    if previous is not None:
        previous.stop()
        widget._fade_animation = None
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)
    animation = QPropertyAnimation(effect, b"opacity", widget)
    animation.setDuration(duration)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def finish() -> None:
        if widget.graphicsEffect() is effect:
            widget.setGraphicsEffect(None)
        if getattr(widget, "_fade_animation", None) is animation:
            widget._fade_animation = None

    animation.finished.connect(finish)
    widget._fade_animation = animation
    animation.start(QPropertyAnimation.DeletionPolicy.KeepWhenStopped)


class _SnapshotOverlay(QWidget):
    """Static snapshot drawn with a fade, deliberately free of graphics effects.

    QGraphicsOpacityEffect on a child of the shadowed panels is rendered with
    an offset (nested effects), which made the old page appear as a floating
    ghost. Painting the pixmap ourselves keeps the crossfade exactly on top of
    the page it belongs to.

    The overlay keeps mouse input while it fades: otherwise a click during the
    transition reaches the freshly shown page and the old page (for the market
    detail it is the previous product with its chart and prices) stays on
    screen for a moment on top of the new one.
    """

    def __init__(self, parent: QWidget, pixmap: QPixmap) -> None:
        super().__init__(parent)
        self.setObjectName("CrossfadeOverlay")
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self._pixmap = pixmap
        self._opacity = 1.0

    def set_opacity(self, value: float) -> None:
        self._opacity = max(0.0, min(1.0, value))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        if self._pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setOpacity(self._opacity)
        painter.drawPixmap(self.rect(), self._pixmap)
        painter.end()


def clear_crossfade(stack: QStackedWidget) -> None:
    """Drop a running snapshot fade, so the next page switch is immediate."""
    animation = getattr(stack, "_crossfade_animation", None)
    overlay = getattr(stack, "_crossfade_overlay", None)
    if animation is not None:
        animation.stop()
    if overlay is not None:
        overlay.hide()
        overlay.deleteLater()
    stack._crossfade_animation = None
    stack._crossfade_overlay = None


def crossfade_stack(
    stack: QStackedWidget,
    target: QWidget,
    duration: int = 170,
    update: Callable[[], None] | None = None,
) -> None:
    """Switch a stacked page with a snapshot crossfade.

    The old view is captured before ``update`` runs, then faded out over the
    new content. Unlike applying an opacity effect to a live stack page, this
    cannot reveal hidden sibling pages and never blanks the area during the
    switch. ``update`` also covers in-place rebuilds of the same page (for
    example switching between history categories).
    """
    previous_animation = getattr(stack, "_crossfade_animation", None)
    previous_overlay = getattr(stack, "_crossfade_overlay", None)
    if previous_animation is not None:
        previous_animation.stop()
    if previous_overlay is not None:
        previous_overlay.hide()
        previous_overlay.deleteLater()
        stack._crossfade_overlay = None

    same_page = stack.currentWidget() is target
    if same_page and update is None:
        return

    snapshot = None
    if stack.isVisible() and stack.width() > 1 and stack.height() > 1:
        snapshot = stack.grab()
    if snapshot is None or snapshot.isNull():
        if update is not None:
            update()
        if not same_page:
            stack.setCurrentWidget(target)
        return

    # Снимок старого вида должен оказаться в заднем буфере ДО того, как
    # покажется новая страница. Иначе окно успевает вывести один кадр новой
    # страницы (в маркете это карточка товара с ценами и графиком), и только
    # следующим кадром её накрывает снимок — получается вспышка.
    overlay = _SnapshotOverlay(stack, snapshot)
    overlay.setGeometry(stack.rect())
    overlay.show()
    overlay.raise_()
    overlay.repaint()
    stack._crossfade_overlay = overlay

    if update is not None:
        update()
    if not same_page:
        stack.setCurrentWidget(target)
    overlay.raise_()
    # Страница могла успеть отрисоваться прямо во время переключения —
    # возвращаем снимок наверх синхронно, до следующего кадра.
    overlay.repaint()

    animation = QVariantAnimation(overlay)
    animation.setDuration(duration)
    animation.setStartValue(1.0)
    animation.setEndValue(0.0)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    animation.valueChanged.connect(
        lambda value: overlay.set_opacity(float(value))
    )

    def finish() -> None:
        if getattr(stack, "_crossfade_overlay", None) is overlay:
            stack._crossfade_overlay = None
            overlay.hide()
            overlay.deleteLater()
        if getattr(stack, "_crossfade_animation", None) is animation:
            stack._crossfade_animation = None

    animation.finished.connect(finish)
    stack._crossfade_overlay = overlay
    stack._crossfade_animation = animation
    animation.start(QVariantAnimation.DeletionPolicy.KeepWhenStopped)


class HoverSurface:
    """Animated hover tint for cards, 120-180 ms.

    The QSS still owns the resting look; this mixin only paints a smooth
    transition towards the hover surface colour, so no per-colour styles are
    needed and both themes keep working through the design tokens.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._hover_progress = 0.0
        self._hover_animation = QVariantAnimation(self)
        self._hover_animation.setDuration(150)
        self._hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_animation.valueChanged.connect(self._on_hover_value)

    def _on_hover_value(self, value: float) -> None:
        self._hover_progress = float(value)
        self.update()

    def _animate_hover(self, target: float) -> None:
        animation = getattr(self, "_hover_animation", None)
        if animation is None:
            return
        animation.stop()
        animation.setStartValue(self._hover_progress)
        animation.setEndValue(target)
        animation.start()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._animate_hover(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._animate_hover(0.0)
        super().leaveEvent(event)

    def _hover_palette(self) -> tuple[str, str, float]:
        tokens = design.tokens(theme.active_theme())
        return tokens.card, tokens.card_hover, float(design.RADIUS["card"])

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        progress = getattr(self, "_hover_progress", 0.0)
        base, hover, radius = self._hover_palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(design.blend(base, hover, progress))
        inset = 1.6
        rect = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)
        painter.drawRoundedRect(rect, radius - inset, radius - inset)


class HoverCard(HoverSurface, QFrame):
    """QFrame with the animated card hover surface."""


class PressFeedback(QObject):
    """Short, subtle press feedback for every button (100-150 ms)."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if isinstance(obj, QAbstractButton) and obj.isEnabled():
            kind = event.type()
            if kind == QEvent.Type.MouseButtonPress:
                self._animate(obj, 0.88, 110, remove=False)
            elif kind in (
                QEvent.Type.MouseButtonRelease,
                QEvent.Type.Leave,
            ):
                # Только если кнопка действительно была нажата. Раньше эффект
                # создавался даже при обычном уходе курсора, из-за чего
                # кнопка/подпись на мгновение пропадала.
                if getattr(obj, "_press_effect", None) is not None:
                    self._animate(obj, 1.0, 120, remove=True)
        return False

    @staticmethod
    def _animate(
        button: QAbstractButton,
        target: float,
        duration: int,
        *,
        remove: bool,
    ) -> None:
        animation = getattr(button, "_press_animation", None)
        if animation is not None:
            animation.stop()
        effect = getattr(button, "_press_effect", None)
        if effect is None:
            if button.graphicsEffect() is not None:
                return
            effect = QGraphicsOpacityEffect(button)
            effect.setOpacity(1.0)
            button._press_effect = effect
            button.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", button)
        animation.setDuration(duration)
        animation.setStartValue(effect.opacity())
        animation.setEndValue(target)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        def finish() -> None:
            if remove and getattr(button, "_press_effect", None) is effect:
                button.setGraphicsEffect(None)
                button._press_effect = None
            if getattr(button, "_press_animation", None) is animation:
                button._press_animation = None

        animation.finished.connect(finish)
        button._press_animation = animation
        animation.start()


def install_press_feedback(app: QApplication) -> PressFeedback:
    """Install one application-wide press animator (idempotent)."""
    existing = getattr(app, "_galardo_press_feedback", None)
    if isinstance(existing, PressFeedback):
        return existing
    feedback = PressFeedback(app)
    app._galardo_press_feedback = feedback
    app.installEventFilter(feedback)
    return feedback


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


class HoverClickableFrame(HoverSurface, ClickableFrame):
    """Clickable frame with the animated card hover surface."""


class HoverHeader(HoverClickableFrame):
    """Week header with its own neutral header palette."""

    def _hover_palette(self) -> tuple[str, str, float]:
        theme_name = theme.active_theme()
        tokens = design.tokens(theme_name)
        light = theme_name == "light"
        base = design.mix(tokens.panel, tokens.surface, 0.30 if not light else 0.55)
        hover = design.mix(
            tokens.panel, tokens.surface_hover, 0.42 if not light else 0.78
        )
        return base, hover, float(design.RADIUS["header"])


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
        self._shadow = shadow
        shadow.setColor(QColor(0, 0, 0, 170))
        self.card.setGraphicsEffect(shadow)
        outer.addWidget(self.card)

        self.body = QVBoxLayout(self.card)
        self.body.setContentsMargins(12, 12, 12, 12)
        self.body.setSpacing(10)

        QShortcut(QKeySequence(Qt.Key.Key_Escape), self).activated.connect(self.close)

    def refresh_shadow(self, theme_name: str, accent: str) -> None:
        self._shadow.setColor(
            theme.shadow_color(theme_name, accent, strong=True)
        )

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
    tokens = design.tokens(theme_name)
    ring = tokens.text
    hover = design.rgba(tokens.text, 0.45)
    border = f"2px solid {ring}" if selected else "2px solid transparent"
    return (
        "QPushButton {"
        f" background-color: {color};"
        f" border: {border};"
        " border-radius: 14px;"
        " padding: 0px;"
        " min-width: 0px;"
        "}"
        f"QPushButton:hover {{ border-color: {hover}; }}"
    )


class SettingsPopup(PopupBase):
    accentChanged = Signal(str)
    themeChanged = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._accent = theme.DEFAULT_ACCENT
        self._theme_name = theme.DEFAULT_THEME

        title = QLabel("Оформление")
        title.setObjectName("PopupTitle")
        self.body.addWidget(title)

        hint = QLabel("Настройте внешний вид под себя")
        hint.setObjectName("PopupHint")
        self.body.addWidget(hint)

        theme_label = ui_kit.SectionHeader("Тема")
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

        accent_label = ui_kit.SectionHeader("Вторичный цвет")
        self.body.addWidget(accent_label)

        accent_row = QHBoxLayout()
        accent_row.setSpacing(8)
        self._swatches: dict[str, QPushButton] = {}
        for key, (color, name) in theme.ACCENTS.items():
            button = QPushButton()
            button.setFixedSize(28, 28)
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

        preview = QFrame()
        preview.setObjectName("AccentPreview")
        preview_row = QHBoxLayout(preview)
        preview_row.setContentsMargins(10, 7, 10, 7)
        preview_row.setSpacing(9)
        dot = QLabel()
        dot.setObjectName("AccentPreviewDot")
        dot.setFixedSize(14, 14)
        preview_row.addWidget(dot)
        caption = QLabel("Текущий акцент")
        caption.setObjectName("AccentPreviewLabel")
        preview_row.addWidget(caption)
        preview_row.addStretch(1)
        self._accent_value = QLabel(self._accent.upper())
        self._accent_value.setObjectName("AccentPreviewValue")
        preview_row.addWidget(self._accent_value)
        self.body.addWidget(preview)

    def open_for(
        self,
        anchor: QWidget,
        accent: str,
        theme_name: str,
    ) -> None:
        self._accent = accent
        self._theme_name = theme_name if theme_name in theme.THEMES else theme.DEFAULT_THEME
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
        self._accent_value.setText(self._accent.upper())

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


# ----------------------------------------------------------------------------- photo
class PhotoDrop(QFrame):
    photoAdded = Signal()
    photoReplaced = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PhotoDrop")
        self.setProperty("filled", False)
        self.setFixedHeight(104)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAcceptDrops(True)
        self.setToolTip("Ctrl+V — вставить фото из буфера обмена")

        self._bytes: bytes | None = None
        self._image: QImage | None = None
        self._file_name = ""

        self._empty_pixmap = icons.icon_pixmap(
            "photo", theme.icon_tone("text"), 96
        ).scaled(
            48,
            48,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._empty_pixmap.setDevicePixelRatio(2.0)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        self._preview = QLabel()
        self._preview.setObjectName("PhotoIcon")
        self._preview.setFixedSize(72, 72)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setPixmap(self._empty_pixmap)
        layout.addWidget(self._preview)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)
        self._title = QLabel("Добавить фотографию")
        self._title.setObjectName("PhotoTitle")
        self._title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._hint = QLabel("Перетащите изображение или нажмите для выбора")
        self._hint.setObjectName("PhotoHint")
        self._hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._hint.setWordWrap(True)
        text_layout.addWidget(self._title)
        text_layout.addWidget(self._hint)
        layout.addLayout(text_layout, 1)

        actions = QVBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(5)

        self._replace = QPushButton("Заменить")
        self._replace.setObjectName("Chip")
        self._replace.setCursor(Qt.CursorShape.PointingHandCursor)
        self._replace.setFixedHeight(28)
        self._replace.setIconSize(QSize(13, 13))
        self._replace.setToolTip("Заменить фотографию")
        self._replace.setIcon(icons.icon("pencil", theme.icon_tone("muted")))
        self._replace.clicked.connect(self._pick)
        self._replace.hide()
        actions.addWidget(self._replace)

        self._clear = QPushButton("Удалить")
        self._clear.setObjectName("Chip")
        self._clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear.setFixedHeight(28)
        self._clear.setIconSize(QSize(13, 13))
        self._clear.setToolTip("Удалить фотографию")
        self._clear.setIcon(icons.icon("trash", theme.icon_tone("muted")))
        self._clear.clicked.connect(self.clear)
        self._clear.hide()
        actions.addWidget(self._clear)

        layout.addLayout(actions)

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
        had_photo = bool(self._bytes)
        self._image = image
        self._bytes = image_to_jpeg(image)
        self._file_name = file_name
        self._update_view()
        if had_photo:
            self.photoReplaced.emit()
        else:
            self.photoAdded.emit()

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
        self._title.setText("Добавить фотографию")
        self._hint.setText("Перетащите изображение или нажмите для выбора")
        self._hint.setToolTip("")
        self._replace.hide()
        self._clear.hide()

    def refresh_icons(self) -> None:
        self._empty_pixmap = icons.icon_pixmap(
            "photo", theme.icon_tone("text"), 96
        ).scaled(
            48,
            48,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._empty_pixmap.setDevicePixelRatio(2.0)
        self._replace.setIcon(icons.icon("pencil", theme.icon_tone("muted")))
        self._clear.setIcon(icons.icon("trash", theme.icon_tone("muted")))
        if self.has_photo() and self._image is not None:
            self._preview.setPixmap(
                rounded_image_pixmap(self._image, 72, 72, 12.0)
            )
        else:
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
            rounded_image_pixmap(self._image, 72, 72, 12.0)
        )
        self._title.setText("Фотография добавлена")
        hint = self._file_name or "Нажмите на область, чтобы заменить"
        self._hint.setText(hint)
        self._hint.setToolTip(safe_tooltip(self._file_name) if self._file_name else "")
        self._replace.show()
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


class DealCard(HoverCard):
    editRequested = Signal(int)
    deleteRequested = Signal(int)
    copyRequested = Signal(int)
    quickRequested = Signal(int, str)
    photoRequested = Signal(int)
    statsRequested = Signal(int)

    def __init__(self, deal: Deal, currency: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.deal = deal
        self._photo_bytes = deal.photo
        self._photo_clickable = False
        self.setObjectName("DealCard")
        self.setProperty("side", deal.side)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self._drag_handle: DragHandle | None = None

        self._main_layout = QHBoxLayout(self)
        self._main_layout.setContentsMargins(12, 10, 10, 10)
        self._main_layout.setSpacing(12)

        self._thumb = QLabel()
        self._thumb.setObjectName("DealThumb")
        self._thumb.setFixedSize(52, 52)
        self._thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._main_layout.addWidget(self._thumb, 0, Qt.AlignmentFlag.AlignTop)
        self._set_thumb()

        body = QVBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(5)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(7)
        badge = ui_kit.Badge(
            "Купил" if deal.side == "buy" else "Продал",
            tone="loss" if deal.side == "buy" else "profit",
        )
        header.addWidget(badge)

        title = ElidedLabel(deal.product)
        title.setObjectName("DealTitle")
        title.setMinimumWidth(70)
        title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        title.setCursor(Qt.CursorShape.PointingHandCursor)
        title.setToolTip(
            safe_tooltip(f"{deal.product} · статистика за 30 дней")
        )
        title.clicked.connect(lambda: self.statsRequested.emit(deal.id))
        header.addWidget(title, 1)

        amount = QLabel(format_money(deal.signed_amount, currency))
        amount.setObjectName("AmountBuy" if deal.side == "buy" else "AmountSell")
        header.addWidget(amount, 0, Qt.AlignmentFlag.AlignVCenter)
        body.addLayout(header)

        meta = QHBoxLayout()
        meta.setContentsMargins(0, 0, 0, 0)
        meta.setSpacing(5)
        category = QLabel(CATEGORIES.get(deal.category, deal.category))
        category.setObjectName("DealCategory")
        meta.addWidget(category)
        dot = QLabel("·")
        dot.setObjectName("DealMetaDot")
        meta.addWidget(dot)
        date = QDateTime.fromString(deal.dealt_at, Qt.DateFormat.ISODate)
        date_text = date.toString("dd.MM.yy HH:mm") if date.isValid() else deal.dealt_at
        date_label = QLabel(date_text)
        date_label.setObjectName("DealDate")
        meta.addWidget(date_label)
        meta.addStretch(1)
        body.addLayout(meta)

        if deal.comment:
            comment = ElidedLabel(deal.comment)
            comment.setObjectName("DealComment")
            comment.setToolTip(safe_tooltip(deal.comment))
            body.addWidget(comment)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(6)
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
        body.addLayout(actions)
        self._main_layout.addLayout(body, 1)

        actions_column = QVBoxLayout()
        actions_column.setContentsMargins(0, 0, 0, 0)
        actions_column.setSpacing(3)
        actions_column.setAlignment(Qt.AlignmentFlag.AlignTop)

        edit_button = make_icon_button("pencil", "Редактировать сделку")
        edit_button.clicked.connect(lambda: self.editRequested.emit(deal.id))
        actions_column.addWidget(edit_button)
        self._edit_button = edit_button

        delete_button = make_icon_button("trash", "Удалить сделку")
        delete_button.clicked.connect(lambda: self.deleteRequested.emit(deal.id))
        actions_column.addWidget(delete_button)
        self._delete_button = delete_button

        copy_button = make_icon_button("copy", "Копировать сделку")
        copy_button.clicked.connect(lambda: self.copyRequested.emit(deal.id))
        actions_column.addWidget(copy_button)
        self._copy_button = copy_button

        self._main_layout.addLayout(actions_column)

    def _hover_palette(self) -> tuple[str, str, float]:
        theme_name = theme.active_theme()
        tokens = design.tokens(theme_name)
        light = theme_name == "light"
        if bool(self.property("embedded")):
            base = design.mix(tokens.card, tokens.bg, 0.30 if not light else 0.18)
            hover = design.mix(
                tokens.card, tokens.surface_hover, 0.45 if not light else 0.55
            )
            return base, hover, float(design.RADIUS["row"])
        return tokens.card, tokens.card_hover, float(design.RADIUS["card"])

    def _set_thumb(self) -> None:
        image = QImage.fromData(self._photo_bytes) if self._photo_bytes else QImage()
        if not image.isNull():
            thumb = ClickableLabel()
            thumb.setObjectName("DealThumb")
            thumb.setFixedSize(52, 52)
            thumb.setCursor(Qt.CursorShape.PointingHandCursor)
            thumb.setToolTip("Открыть фото")
            thumb.setPixmap(rounded_image_pixmap(image, 52, 52, 10.0))
            thumb.clicked.connect(
                lambda: self.photoRequested.emit(self.deal.id)
            )
            old = self._main_layout.itemAt(0).widget()
            self._main_layout.replaceWidget(old, thumb)
            old.deleteLater()
            self._thumb = thumb
            self._photo_clickable = True
            return

        pixmap = icons.icon_pixmap(
            "photo", theme.icon_tone("faint"), 72
        ).scaled(
            24,
            24,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._thumb.setPixmap(pixmap)
        self._thumb.setCursor(Qt.CursorShape.ArrowCursor)
        self._thumb.setToolTip("Фото не добавлено")
        self._photo_clickable = False

    def enable_drag(self, deal_ids: list[int], week: int) -> None:
        if self._drag_handle is not None:
            return
        self._drag_handle = DragHandle(deal_ids, week, self)
        self._main_layout.insertWidget(0, self._drag_handle)

    def refresh_icons(self) -> None:
        tone = theme.icon_tone("muted")
        self._edit_button.setIcon(icons.icon("pencil", tone))
        self._delete_button.setIcon(icons.icon("trash", tone))
        self._copy_button.setIcon(icons.icon("copy", tone))
        if not self._photo_clickable:
            pixmap = icons.icon_pixmap(
                "photo", theme.icon_tone("faint"), 72
            ).scaled(
                24,
                24,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._thumb.setPixmap(pixmap)
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
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(7)

        self._header = HoverHeader()
        self._header.setObjectName("WeekHeader")
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        header = QHBoxLayout(self._header)
        header.setContentsMargins(11, 8, 13, 8)
        header.setSpacing(9)

        self._chevron = QLabel("▾" if expanded else "▸")
        self._chevron.setObjectName("WeekChevron")
        self._chevron.setFixedWidth(12)
        header.addWidget(self._chevron)

        number_label = QLabel(f"Неделя {number}")
        number_label.setObjectName("WeekNumber")
        header.addWidget(number_label)

        range_label = QLabel(
            f"{start.toString('dd.MM')} – {end.toString('dd.MM')}"
        )
        range_label.setObjectName("WeekRange")
        header.addWidget(range_label)
        header.addStretch(1)

        meta = QLabel(f"{count} {deals_word(count)}")
        meta.setObjectName("WeekMeta")
        header.addWidget(meta)

        amount = QLabel(format_money(total, currency))
        amount.setObjectName("WeekAmount")
        amount.setProperty(
            "state",
            "positive" if total > 0.004 else "negative" if total < -0.004 else "",
        )
        header.addWidget(amount)
        outer.addWidget(self._header)

        # Parent from the start: a parentless QWidget shown before being added
        # to a layout briefly becomes a native top-level window (a visible
        # flash plus a focus flicker) every time the history is rebuilt.
        self.body = QWidget(self)
        self.body.setObjectName("WeekBody")
        self.body.setAcceptDrops(True)
        self.body.installEventFilter(self)
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(8)
        self.body.setVisible(expanded)
        outer.addWidget(self.body)

        self._animation = QPropertyAnimation(self.body, b"maximumHeight", self)
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.finished.connect(self._on_expand_finished)

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
        self._chevron.setText("▾" if self._expanded else "▸")
        self._animation.stop()
        if self._expanded:
            self.body.setMaximumHeight(0)
            self.body.setVisible(True)
            self.body.updateGeometry()
            target = self.body.sizeHint().height()
            self._animation.setStartValue(0)
            self._animation.setEndValue(max(0, target))
            self._animation.start()
        else:
            self.body.setVisible(False)
            self.body.setMaximumHeight(0)
            layout = self.layout()
            if layout is not None:
                layout.invalidate()
            self.updateGeometry()
            QTimer.singleShot(0, self._sync_collapsed_layout)
        self.toggled.emit(self._expanded)

    def _sync_collapsed_layout(self) -> None:
        if self._expanded:
            return
        layout = self.layout()
        if layout is not None:
            layout.invalidate()
        self.updateGeometry()
        parent = self.parentWidget()
        if parent is not None:
            parent_layout = parent.layout()
            if parent_layout is not None:
                parent_layout.invalidate()
            parent.updateGeometry()

    def _on_expand_finished(self) -> None:
        if self._expanded:
            self.body.setMaximumHeight(16777215)

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
class PairSection(QFrame):
    """Единая карточка связанной пары «покупка + продажа»."""

    toggled = Signal(bool)
    statsRequested = Signal(int)
    editRequested = Signal(int)
    deleteRequested = Signal(int)
    copyRequested = Signal(int)

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
        sale_total = sum(item.amount for item in children)
        state = (
            "positive" if total > 0.004 else "negative" if total < -0.004 else ""
        )

        self.setObjectName("PairCard")
        self.setProperty("state", state)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._strip = QFrame()
        self._strip.setObjectName("PairStrip")
        self._strip.setProperty("state", state)
        self._strip.setFixedWidth(3)
        outer.addWidget(self._strip)

        content = QWidget()
        content.setObjectName("PairContent")
        inner = QVBoxLayout(content)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(0)
        outer.addWidget(content, 1)

        self._header = ClickableFrame()
        self._header.setObjectName("PairHeader")
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        header = QHBoxLayout(self._header)
        header.setContentsMargins(10, 9, 10, 9)
        header.setSpacing(9)
        self._header_layout = header

        self._chevron = QLabel("▾" if expanded else "▸")
        self._chevron.setObjectName("PairChevron")
        self._chevron.setFixedWidth(12)
        header.addWidget(self._chevron)

        self._thumb = QLabel()
        self._thumb.setObjectName("DealThumb")
        self._thumb.setFixedSize(48, 48)
        self._thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        header.addWidget(self._thumb, 0, Qt.AlignmentFlag.AlignVCenter)

        body = QVBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(4)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)
        title = ElidedLabel(deal.product)
        title.setObjectName("PairTitle")
        title.setMinimumWidth(80)
        title.setCursor(Qt.CursorShape.PointingHandCursor)
        title.setToolTip(
            safe_tooltip(f"{deal.product} · статистика за 30 дней")
        )
        title.clicked.connect(lambda: self.statsRequested.emit(deal.id))
        title_row.addWidget(title, 1)

        profit = QLabel(format_money(total, currency))
        profit.setObjectName("PairProfit")
        profit.setProperty("state", state)
        title_row.addWidget(profit, 0, Qt.AlignmentFlag.AlignVCenter)
        body.addLayout(title_row)

        start_dt = QDateTime.fromString(deal.dealt_at, Qt.DateFormat.ISODate)
        dates = [
            QDateTime.fromString(item.dealt_at, Qt.DateFormat.ISODate)
            for item in members
        ]
        dates = [item for item in dates if item.isValid()]
        if dates:
            first = min(dates)
            last = max(dates)
            if first.date() == last.date():
                date_text = first.toString("dd.MM.yy")
            else:
                date_text = (
                    f"{first.toString('dd.MM.yy')} → {last.toString('dd.MM.yy')}"
                )
        elif start_dt.isValid():
            date_text = start_dt.toString("dd.MM.yy")
        else:
            date_text = deal.dealt_at

        # одна эластичная строка: на узком окне хвост аккуратно сокращается,
        # а не выталкивает цены и кнопки за правый край карточки
        meta_text = (
            f"Покупка {format_money(deal.amount, currency, with_sign=False)}"
            " · "
            f"Продажа {format_money(sale_total, currency, with_sign=False)}"
            f" · {date_text}"
        )
        meta = ElidedLabel(meta_text)
        meta.setObjectName("PairMeta")
        meta.setToolTip(safe_tooltip(meta_text))
        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(0)
        meta_row.addWidget(meta, 1)
        body.addLayout(meta_row)
        header.addLayout(body, 1)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(3)
        edit_button = make_icon_button("pencil", "Редактировать покупку")
        edit_button.clicked.connect(lambda: self.editRequested.emit(deal.id))
        actions.addWidget(edit_button)
        self._edit_button = edit_button

        delete_button = make_icon_button("trash", "Удалить покупку")
        delete_button.clicked.connect(lambda: self.deleteRequested.emit(deal.id))
        actions.addWidget(delete_button)
        self._delete_button = delete_button

        copy_button = make_icon_button("copy", "Копировать пару")
        copy_button.clicked.connect(lambda: self.copyRequested.emit(deal.id))
        actions.addWidget(copy_button)
        self._copy_button = copy_button
        header.addLayout(actions)
        inner.addWidget(self._header)

        self.body = QWidget(self)
        self.body.setObjectName("PairBody")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(16, 0, 12, 10)
        self.body_layout.setSpacing(6)
        self.body.setVisible(expanded)
        inner.addWidget(self.body)

        self._animation = QPropertyAnimation(self.body, b"maximumHeight", self)
        self._animation.setDuration(180)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.finished.connect(self._on_expand_finished)

        self._header.clicked.connect(self._toggle)
        self._set_thumb()
        self._apply_photo(deal, children)

    def _apply_photo(self, deal: Deal, children: list[Deal]) -> None:
        self._photo_deal = deal
        for item in children:
            if item.photo:
                self._photo_deal = item
                break
        self._set_thumb()

    def _set_thumb(self) -> None:
        data = getattr(self, "_photo_deal", None)
        image = QImage.fromData(data.photo) if data and data.photo else QImage()
        if not image.isNull():
            self._thumb.setPixmap(rounded_image_pixmap(image, 48, 48, 9.0))
            self._thumb.setToolTip("Открыть фото")
        else:
            pixmap = icons.icon_pixmap(
                "photo", theme.icon_tone("faint"), 72
            ).scaled(
                22,
                22,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._thumb.setPixmap(pixmap)
            self._thumb.setToolTip("Фото не добавлено")

    def add_card(self, card: QWidget) -> None:
        card.setProperty("embedded", True)
        repolish(card)
        self.body_layout.addWidget(card)

    def enable_drag(self, deal_ids: list[int], week: int) -> None:
        if self._drag_handle is not None or self._header_layout is None:
            return
        self._drag_handle = DragHandle(deal_ids, week, self._header)
        self._header_layout.insertWidget(1, self._drag_handle)

    def refresh_icons(self) -> None:
        tone = theme.icon_tone("muted")
        self._edit_button.setIcon(icons.icon("pencil", tone))
        self._delete_button.setIcon(icons.icon("trash", tone))
        self._copy_button.setIcon(icons.icon("copy", tone))
        self._set_thumb()
        for index in range(self.body_layout.count()):
            item = self.body_layout.itemAt(index)
            widget = item.widget() if item is not None else None
            if isinstance(widget, DealCard):
                widget.refresh_icons()
        if self._drag_handle is not None:
            self._drag_handle.update()

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        self._chevron.setText("▾" if self._expanded else "▸")
        self._animation.stop()
        if self._expanded:
            self.body.setMaximumHeight(0)
            self.body.setVisible(True)
            self.body.updateGeometry()
            target = self.body.sizeHint().height()
            self._animation.setStartValue(0)
            self._animation.setEndValue(max(0, target))
            self._animation.start()
        else:
            self.body.setVisible(False)
            self.body.setMaximumHeight(0)
            layout = self.layout()
            if layout is not None:
                layout.invalidate()
            self.updateGeometry()
            QTimer.singleShot(0, self._sync_collapsed_layout)
        self.toggled.emit(self._expanded)

    def _sync_collapsed_layout(self) -> None:
        if self._expanded:
            return
        layout = self.layout()
        if layout is not None:
            layout.invalidate()
        self.updateGeometry()
        parent = self.parentWidget()
        if parent is not None:
            parent_layout = parent.layout()
            if parent_layout is not None:
                parent_layout.invalidate()
            parent.updateGeometry()

    def _on_expand_finished(self) -> None:
        if self._expanded:
            self.body.setMaximumHeight(16777215)



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
        self.setFixedHeight(58)
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

        # centre: live journal metrics -----------------------------------------
        self._stats = QFrame()
        self._stats.setObjectName("TopStats")
        self._stats.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        stats_box = QHBoxLayout(self._stats)
        stats_box.setContentsMargins(14, 5, 14, 5)
        stats_box.setSpacing(16)

        self._stat_total = QLabel("$ 0")
        self._stat_total.setObjectName("TopStatValue")
        self._stat_total.setProperty("state", "")
        closed_value = QLabel("0")
        closed_value.setObjectName("TopStatValue")
        active_value = QLabel("0")
        active_value.setObjectName("TopStatValue")
        self._stat_closed = closed_value
        self._stat_active = active_value

        def add_metric(value: QLabel, caption: str) -> None:
            box = QVBoxLayout()
            box.setContentsMargins(0, 0, 0, 0)
            box.setSpacing(0)
            value.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
            )
            box.addWidget(value)
            label = QLabel(caption)
            label.setObjectName("TopStatLabel")
            label.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
            )
            box.addWidget(label)
            stats_box.addLayout(box)

        def add_divider() -> None:
            divider = QFrame()
            divider.setObjectName("TopDivider")
            divider.setFixedSize(1, 26)
            divider.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
            )
            stats_box.addWidget(divider, 0, Qt.AlignmentFlag.AlignVCenter)

        add_metric(self._stat_total, "Общая прибыль")
        add_divider()
        add_metric(closed_value, "Закрыто")
        add_divider()
        add_metric(active_value, "Активно")
        layout.addWidget(self._stats, 0, Qt.AlignmentFlag.AlignVCenter)
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

    def set_stats(
        self,
        total: float,
        closed: int,
        active: int,
        currency: str = "$",
    ) -> None:
        """Show journal-wide figures in the centre of the title bar."""
        self._stat_total.setText(format_money(total, currency))
        state = (
            "negative"
            if total < -0.0001
            else "positive"
            if total > 0.0001
            else ""
        )
        self._stat_total.setProperty("state", state)
        repolish(self._stat_total)
        self._stat_closed.setText(str(max(0, closed)))
        self._stat_active.setText(str(max(0, active)))

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
        self._animation.setDuration(200)
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
        self._animation.setDuration(220)
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
