"""Centralized design system for Galardo.

The module keeps every visual constant in one place: colour roles for the
dark and light themes, the accent presets, radii, spacing and the type scale.
``galardo.theme`` turns these tokens into QSS, so a component never needs its
own colours and both themes always stay in sync.

Style direction: Minimal Premium + Gaming Luxury.  Graphite surfaces, thin
borders, restrained gradients and a single adaptive accent colour.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtGui import QColor, QFont, QFontDatabase

from .paths import resource_path

# --------------------------------------------------------------------- geometry
# Radii follow the redesign brief: panels 20-24, cards 14-18, fields 12-14,
# buttons 10-12.  Smaller values are used for chips, badges and icon buttons.
RADIUS: dict[str, int] = {
    "panel": 22,
    "popup": 18,
    "card": 16,
    "card_large": 18,
    "row": 14,
    "header": 12,
    "field": 13,
    "button": 11,
    "tab": 10,
    "chip": 9,
    "icon": 9,
    "badge": 7,
}

SPACE: dict[str, int] = {
    "xxs": 4,
    "xs": 6,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 22,
    "xxl": 28,
}

# ----------------------------------------------------------------- typography
# One scale for the whole application.  ``(pixel size, weight)`` pairs.
TYPE_SCALE: dict[str, tuple[int, int]] = {
    "display": (22, 700),
    "title": (17, 700),
    "subtitle": (14, 600),
    "body": (13, 400),
    "body_strong": (13, 600),
    "label": (12, 500),
    "caption": (11, 400),
    "micro": (10, 500),
}

FONT_CANDIDATES = ("Inter", "Manrope", "Segoe UI")
FONT_FILES = (
    "Inter-Regular.ttf",
    "Inter-Medium.ttf",
    "Inter-SemiBold.ttf",
    "Inter-Bold.ttf",
)

# --------------------------------------------------------------------- accents
# The standard accent is violet; the rest are the requested presets.
DEFAULT_ACCENT = "#AA8AF5"

ACCENTS: dict[str, tuple[str, str]] = {
    "blue": ("#7795FF", "Синий"),
    "violet": ("#AA8AF5", "Фиолетовый"),
    "emerald": ("#62DDB0", "Зелёный"),
    "amber": ("#F3C45D", "Жёлтый"),
    "rose": ("#F28AA5", "Розовый"),
    "slate": ("#B9C6D8", "Голубой"),
}

# Financial semantics (spec colours for the dark theme).
PROFIT = "#34D399"
LOSS = "#FB7185"

# Shared danger colour (window close button, destructive hover).
DANGER = "#D94147"


@dataclass(frozen=True)
class Theme:
    """Semantic colours for one theme."""

    name: str
    bg: str
    bg_top: str
    bg_bottom: str
    panel: str
    panel_top: str
    card: str
    card_hover: str
    surface: str
    surface_hover: str
    input_bg: str
    input_focus: str
    border: str
    border_soft: str
    border_strong: str
    text: str
    text_soft: str
    muted: str
    faint: str
    profit: str
    loss: str
    overlay: str
    shadow: str
    shadow_soft: str


DARK = Theme(
    name="dark",
    bg="#0B0A10",
    bg_top="#100E17",
    bg_bottom="#08070C",
    panel="#121119",
    panel_top="#17151F",
    card="#1B1923",
    card_hover="#211E2B",
    surface="#252231",
    surface_hover="#2D293A",
    input_bg="#17141F",
    input_focus="#1C1828",
    border="#2C2838",
    border_soft="#211E2B",
    border_strong="#3A3449",
    text="#F5F2FA",
    text_soft="#CFC9DC",
    muted="#A3A0AE",
    faint="#7C7788",
    profit=PROFIT,
    loss=LOSS,
    overlay="rgba(5, 4, 9, 232)",
    shadow="#A6000000",
    shadow_soft="#66000000",
)

LIGHT = Theme(
    name="light",
    bg="#F4F4F7",
    bg_top="#FBFBFD",
    bg_bottom="#EDEDF2",
    panel="#FFFFFF",
    panel_top="#FFFFFF",
    card="#F8F8FB",
    card_hover="#F2F2F7",
    surface="#EFEFF4",
    surface_hover="#E6E6ED",
    input_bg="#FFFFFF",
    input_focus="#FCFCFE",
    border="#E0E0E8",
    border_soft="#EBEBF0",
    border_strong="#CACAD6",
    text="#17171F",
    text_soft="#3B3B47",
    muted="#6B6B77",
    faint="#9494A0",
    # darker variants of the financial colours so text keeps WCAG AA
    profit="#0F7F5A",
    loss="#C23E56",
    overlay="rgba(20, 20, 28, 225)",
    shadow="#33202028",
    shadow_soft="#1F202028",
)

THEME_TOKENS: dict[str, Theme] = {"dark": DARK, "light": LIGHT}


def tokens(theme_name: str = "dark") -> Theme:
    return THEME_TOKENS.get(theme_name, DARK)


# ------------------------------------------------------------------------ fonts
_FONT_FAMILY: str | None = None


def _installed_families() -> set[str]:
    try:
        return {name.lower() for name in QFontDatabase.families()}
    except Exception:  # pragma: no cover - Qt is not initialised yet
        return set()


def _load_bundled_fonts() -> str | None:
    """Register Inter from ``assets/fonts`` when it is shipped with the app."""
    directory = resource_path("assets", "fonts")
    if not isinstance(directory, Path) or not directory.is_dir():
        return None
    loaded = False
    for name in FONT_FILES:
        path = directory / name
        if not path.is_file():
            continue
        try:
            if QFontDatabase.addApplicationFont(str(path)) >= 0:
                loaded = True
        except Exception:  # pragma: no cover - never break the UI over a font
            return None
    if not loaded:
        return None
    families = _installed_families()
    return "Inter" if "inter" in families else None


def font_family() -> str:
    """Inter when available, then Manrope, then the system UI font."""
    global _FONT_FAMILY
    if _FONT_FAMILY:
        return _FONT_FAMILY
    family = _load_bundled_fonts()
    if family is None:
        installed = _installed_families()
        for candidate in FONT_CANDIDATES:
            if candidate.lower() in installed:
                family = candidate
                break
    _FONT_FAMILY = family or "Segoe UI"
    return _FONT_FAMILY


def app_font(point_size: int = 10) -> QFont:
    font = QFont(font_family())
    font.setPointSize(point_size)
    return font


# ------------------------------------------------------------------ colour math
def qcolor(value: str | QColor) -> QColor:
    return value if isinstance(value, QColor) else QColor(value)


def _channel_luminance(value: int) -> float:
    channel = value / 255
    if channel <= 0.03928:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(color: str | QColor) -> float:
    value = qcolor(color)
    return (
        0.2126 * _channel_luminance(value.red())
        + 0.7152 * _channel_luminance(value.green())
        + 0.0722 * _channel_luminance(value.blue())
    )


def contrast_ratio(first: str | QColor, second: str | QColor) -> float:
    one = relative_luminance(first)
    two = relative_luminance(second)
    high, low = max(one, two), min(one, two)
    return (high + 0.05) / (low + 0.05)


def contrast_text(background: str | QColor) -> QColor:
    """White or near-black text, whichever reads better on the background."""
    dark = QColor("#0B0A10")
    light = QColor("#FFFFFF")
    if contrast_ratio(background, dark) >= contrast_ratio(background, light):
        return dark
    return light


def blend(first: str | QColor, second: str | QColor, amount: float) -> QColor:
    one = qcolor(first)
    two = qcolor(second)
    amount = min(1.0, max(0.0, amount))
    return QColor(
        round(one.red() + (two.red() - one.red()) * amount),
        round(one.green() + (two.green() - one.green()) * amount),
        round(one.blue() + (two.blue() - one.blue()) * amount),
    )


def mix(first: str | QColor, second: str | QColor, amount: float) -> str:
    return blend(first, second, amount).name()


def rgba(color: str | QColor, alpha: float) -> str:
    value = qcolor(color)
    return (
        f"rgba({value.red()}, {value.green()}, {value.blue()}, "
        f"{round(min(1.0, max(0.0, alpha)) * 255)})"
    )


def ensure_contrast(
    color: str | QColor,
    background: str | QColor,
    toward_white: bool,
    minimum: float = 4.5,
) -> QColor:
    """Blend towards white or black until the colour is readable."""
    target = QColor("#FFFFFF") if toward_white else QColor("#000000")
    result = QColor(qcolor(color))
    for _step in range(24):
        if contrast_ratio(result, background) >= minimum:
            break
        result = blend(result, target, 0.12)
    return result


# --------------------------------------------------------------- dynamic accent
@dataclass(frozen=True)
class AccentProfile:
    """A complete derived palette for one accent colour and one theme.

    Nothing in the UI hard-codes a hue: every accent shade is generated from
    the user's colour, so presets and custom colours behave identically.
    """

    base: str
    light: str
    dark: str
    soft: str
    soft_strong: str
    border: str
    glow: str
    gradient_from: str
    gradient_to: str
    on: str
    hover: str
    pressed: str


def accent_profile(
    value: str | QColor, theme_name: str = "dark"
) -> AccentProfile:
    """Derive readable accent tones for the active theme."""
    theme = tokens(theme_name)
    light_theme = theme_name == "light"
    raw = QColor(value)
    if not raw.isValid():
        raw = QColor(DEFAULT_ACCENT)

    # The base must stay readable as text on the theme background.
    base = ensure_contrast(
        raw, theme.bg, toward_white=not light_theme, minimum=4.5
    )
    if light_theme:
        light_tone = mix(base, "#FFFFFF", 0.12)
        dark_tone = mix(base, "#000000", 0.18)
        gradient_from = base.name()
        gradient_to = dark_tone
    else:
        light_tone = mix(base, "#FFFFFF", 0.16)
        dark_tone = mix(base, "#000000", 0.18)
        gradient_from = light_tone
        gradient_to = base.name()

    on_accent = contrast_text(base)
    hover = ensure_contrast(
        base.darker(108) if light_theme else base.lighter(108),
        theme.bg,
        toward_white=not light_theme,
        minimum=3.0,
    )
    pressed = ensure_contrast(
        base.darker(116) if light_theme else base.darker(112),
        theme.bg,
        toward_white=not light_theme,
        minimum=3.0,
    )

    return AccentProfile(
        base=base.name(),
        light=light_tone,
        dark=dark_tone,
        soft=rgba(base, 0.15 if light_theme else 0.16),
        soft_strong=rgba(base, 0.24 if light_theme else 0.28),
        border=rgba(base, 0.42 if light_theme else 0.52),
        glow=rgba(base, 0.08 if light_theme else 0.13),
        gradient_from=gradient_from,
        gradient_to=gradient_to,
        on=on_accent.name(),
        hover=hover.name(),
        pressed=pressed.name(),
    )
