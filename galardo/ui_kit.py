"""Reusable visual components for the Galardo design system.

The widgets here only set semantic roles/object names; their appearance lives
in the generated QSS (:mod:`galardo.theme`).  Business widgets keep their own
logic and simply reuse these primitives where a generic component is enough.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolButton,
    QWidget,
)

from . import icons, theme


class Panel(QFrame):
    """Rounded premium surface used for the main columns and overlays."""

    def __init__(self, parent: QWidget | None = None, *, role: str = "panel") -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setProperty("role", role)


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
