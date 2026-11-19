"""Reusable visual components for the Galardo design system.

The widgets here only set semantic roles/object names; their appearance lives
in the generated QSS (:mod:`galardo.theme`).  Business widgets keep their own
logic and simply reuse these primitives where a generic component is enough.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolButton,
    QWidget,
)

from . import design, icons, theme


class Panel(QFrame):
    """Rounded premium surface used for the main columns and overlays."""

    def __init__(self, parent: QWidget | None = None, *, role: str = "panel") -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setProperty("role", role)


class _RibbonSurface:
    def set_ribbon_accent(self, accent: str) -> None:
        self._ribbon_accent = QColor(accent)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        accent = getattr(self, "_ribbon_accent", None)
        if accent is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 10, 10)
        painter.setClipPath(clip)
        width, height = self.width(), self.height()
        design.paint_accent_ribbon(
            painter,
            QRectF(width * 0.26, height * 0.35, width * 0.58, height * 0.9),
            accent,
            0.76 if theme.active_theme() == "dark" else 0.35,
        )


class RibbonFrame(_RibbonSurface, QFrame):
    """A frame with a decorative accent ribbon behind its content."""


class RibbonButton(_RibbonSurface, QPushButton):
    """A push button with a decorative accent ribbon near the bottom."""


class Card(QFrame):
    """Neutral card surface (market rows, stat tiles, transaction cards)."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        kind: str = "card",
        state: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("TransactionCard" if kind == "transaction" else "Card")
        if state:
            self.setProperty("side", state)


class SectionHeader(QLabel):
    """Small caps-like section caption above groups of controls."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("SectionHeader")


class Badge(QLabel):
    """Compact status pill: ``tone`` is accent / profit / loss / muted."""

    def __init__(
        self,
        text: str = "",
        parent: QWidget | None = None,
        *,
        tone: str = "muted",
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName("Badge")
        self.set_tone(tone)

    def set_tone(self, tone: str) -> None:
        self.setProperty("tone", tone)
        style = self.style()
        style.unpolish(self)
        style.polish(self)


class Button(QPushButton):
    """Text button variants sharing the central QSS rules."""

    VARIANTS = {"default": "", "primary": "Primary", "ghost": "Ghost", "chip": "Chip"}

    def __init__(
        self,
        text: str = "",
        parent: QWidget | None = None,
        *,
        variant: str = "default",
    ) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_variant(variant)

    def set_variant(self, variant: str) -> None:
        self.setObjectName(self.VARIANTS.get(variant, ""))


class IconButton(QToolButton):
    """Square icon-only button with a shared hover/focus treatment."""

    def __init__(
        self,
        icon_name: str,
        tooltip: str = "",
        parent: QWidget | None = None,
        *,
        size: int = 15,
        box: int = 25,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("IconBtn")
        self.setIconSize(QSize(size, size))
        self.setFixedSize(box, box)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            self.setToolTip(tooltip)
        self.set_icon(icon_name)

    def set_icon(self, icon_name: str, tone: str | None = None) -> None:
        self.setIcon(icons.icon(icon_name, tone or theme.icon_tone("muted")))


class Input(QLineEdit):
    """Plain text input; focus/error states come from the shared QSS."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Input")

    def set_error(self, has_error: bool) -> None:
        self.setProperty("error", "true" if has_error else "false")
        style = self.style()
        style.unpolish(self)
        style.polish(self)


def set_icon(widget: QToolButton, icon: QIcon) -> None:
    widget.setIcon(icon)
