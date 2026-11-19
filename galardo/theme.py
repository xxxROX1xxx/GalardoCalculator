"""Galardo theme: QSS generated from the central design tokens.

Public API kept for the rest of the application and the test-suite:
``stylesheet``, ``palette``, ``theme_accent``, ``contrast_text``,
``ACCENTS``, ``THEMES``, ``icon_tone``, ``set_active_theme``.

All colours, radii and type sizes come from :mod:`galardo.design`; there are
no per-widget colour overrides.
"""

from __future__ import annotations

import re

from PySide6.QtGui import QColor, QPalette

from . import design

DEFAULT_THEME = "dark"
DEFAULT_ACCENT = design.DEFAULT_ACCENT
ACCENTS: dict[str, tuple[str, str]] = dict(design.ACCENTS)
THEMES: dict[str, str] = {
    "dark": "Чёрная",
    "light": "Белая",
}

_ACTIVE_THEME = DEFAULT_THEME
_ACTIVE_LIQUID_GLASS = False


# ----------------------------------------------------------------------- QSS
QSS_TEMPLATE = r"""
/* --------------------------------------------------------------- foundations */
QWidget {
    color: @TEXT@;
    font-family: "@FONT@";
    font-size: @FS_BODY@px;
}
QLabel {
    background-color: transparent;
}

/* -------------------------------------------------------------------- panels */
QFrame#Panel {
    background: @PANEL_MATERIAL@;
    border: 1px solid @PANEL_EDGE@;
    border-radius: @R_PANEL@px;
}
QLabel#AppTitle {
    color: @TEXT@;
    font-size: @FS_SUBTITLE@px;
    font-weight: 600;
}
QWidget#CrossfadeOverlay {
    background: transparent;
    border: none;
}
QFrame#TopStats {
    background: @TOP_STATS_BG@;
    border: 1px solid @BORDER_SOFT@;
    border-radius: @R_ROW@px;
}
QLabel#TopStatValue {
    color: @TEXT@;
    font-size: @FS_SUBTITLE@px;
    font-weight: 700;
}
QLabel#TopStatValue[state="positive"] { color: @PROFIT@; }
QLabel#TopStatValue[state="negative"] { color: @LOSS@; }
QLabel#TopStatLabel {
    color: @FAINT@;
    font-size: @FS_MICRO@px;
    font-weight: 500;
}
QFrame#TopDivider {
    background-color: @BORDER@;
    border: none;
    border-radius: 0px;
}
QLabel#PanelTitle {
    color: @TEXT@;
    font-size: @FS_DISPLAY@px;
    font-weight: 700;
}
QLabel#PanelSubtitle {
    color: @MUTED@;
    font-size: @FS_LABEL@px;
}
QWidget#FormContent { background-color: transparent; }
QFrame#Divider {
    background-color: @BORDER_SOFT@;
    border: none;
    border-radius: 0px;
}
QLabel#FieldLabel {
    color: @MUTED@;
    font-size: @FS_LABEL@px;
    font-weight: 500;
}
QLabel#SectionHeader {
    color: @MUTED@;
    font-size: @FS_LABEL@px;
    font-weight: 600;
    padding: 2px 0px 6px 0px;
}
QLabel#HistoryPill {
    background: @PILL_BG@;
    border: 1px solid @BORDER@;
    border-radius: @R_TAB@px;
    padding: 7px 14px;
    color: @TEXT_SOFT@;
    font-size: @FS_LABEL@px;
    font-weight: 600;
}
QLabel#CountMuted {
    color: @FAINT@;
    font-size: @FS_CAPTION@px;
}
QPushButton#Tab {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: @R_TAB@px;
    padding: 7px 12px;
    color: @MUTED@;
    font-size: @FS_LABEL@px;
    font-weight: 600;
}
QPushButton#Tab:hover {
    background-color: @SURFACE_SOFT@;
    border-color: @ACCENT_BORDER_SOFT@;
    color: @TEXT@;
}
QPushButton#Tab:checked {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 @ACCENT_SOFT_STRONG@, stop: 0.55 @ACCENT_SOFT@, stop: 1 @ACCENT_GLOW@);
    border-color: @ACCENT_BORDER_SOFT@;
    color: @ACCENT_TEXT@;
    font-weight: 700;
}
QFrame#WeekHeader {
    background: @HEADER_BG@;
    border: 1px solid @BORDER_SOFT@;
    border-radius: @R_HEADER@px;
}
QFrame#WeekHeader:hover {
    background: @HEADER_HOVER@;
    border-color: @BORDER@;
}
QLabel#WeekChevron { color: @MUTED@; font-size: @FS_CAPTION@px; }
QLabel#WeekNumber { color: @TEXT@; font-size: @FS_BODY@px; font-weight: 700; }
QLabel#WeekRange { color: @MUTED@; font-size: @FS_CAPTION@px; }
QLabel#WeekMeta { color: @FAINT@; font-size: @FS_CAPTION@px; }
QLabel#WeekAmount {
    color: @MUTED@;
    font-size: @FS_BODY@px;
    font-weight: 700;
}
QLabel#WeekAmount[state="positive"] { color: @PROFIT@; }
QLabel#WeekAmount[state="negative"] { color: @LOSS@; }
QWidget#WeekBody { background: transparent; }
QLabel#DragHandle {
    background-color: transparent;
    border-radius: @R_BADGE@px;
}
QLabel#DragHandle:hover { background-color: @SURFACE@; }
QLabel#DragHandle:pressed { background-color: @SURFACE_HOVER@; }
QFrame#PairCard {
    background: @PAIR_BG@;
    border: 1px solid @BORDER_SOFT@;
    border-radius: @R_CARD@px;
}
QFrame#PairCard:hover { border-color: @BORDER@; }
QFrame#PairStrip {
    border: none;
    background-color: @BORDER@;
}
QFrame#PairStrip[state="positive"] { background-color: @PROFIT@; }
QFrame#PairStrip[state="negative"] { background-color: @LOSS@; }
QWidget#PairContent { background: transparent; }
QFrame#PairHeader {
    background-color: transparent;
    border: none;
    border-radius: 0px;
}
QFrame#PairHeader:hover { background-color: transparent; }
QFrame#PairHeader:hover QLabel#PairTitle { color: @ACCENT@; }
QFrame#PairHeader:hover QLabel#PairChevron { color: @TEXT_SOFT@; }
QLabel#PairChevron { color: @MUTED@; font-size: @FS_CAPTION@px; }
QLabel#PairTitle { color: @TEXT@; font-size: @FS_SUBTITLE@px; font-weight: 600; }
QLabel#PairProfit {
    color: @MUTED@;
    font-size: @FS_DISPLAY@px;
    font-weight: 700;
}
QLabel#PairProfit[state="positive"] { color: @PROFIT@; }
QLabel#PairProfit[state="negative"] { color: @LOSS@; }
QLabel#PairBuy { color: @TEXT_SOFT@; font-size: @FS_CAPTION@px; }
QLabel#PairSell { color: @TEXT_SOFT@; font-size: @FS_CAPTION@px; }
QLabel#PairDate { color: @FAINT@; font-size: @FS_CAPTION@px; }
QLabel#PairMeta { color: @TEXT_SOFT@; font-size: @FS_CAPTION@px; }
QLabel#PairMetaDot { color: @FAINT@; font-size: @FS_CAPTION@px; }
QWidget#PairBody { background: transparent; }
QFrame#DropLine {
    background-color: @ACCENT@;
    border: none;
    border-radius: 1px;
}
QLabel#DealTitle { color: @TEXT@; font-size: @FS_BODY@px; font-weight: 600; }
QLabel#DealCategory { color: @MUTED@; font-size: @FS_CAPTION@px; }
QLabel#DealMetaDot { color: @FAINT@; font-size: @FS_CAPTION@px; }
QLabel#DealDate { color: @FAINT@; font-size: @FS_CAPTION@px; }
QLabel#DealComment { color: @MUTED@; font-size: @FS_CAPTION@px; font-style: italic; }
QLabel#DealThumb {
    background-color: @SURFACE_SOFT@;
    border: 1px solid @BORDER_SOFT@;
    border-radius: @R_ROW@px;
}
QLabel#EmptyTitle { color: @TEXT_SOFT@; font-size: @FS_SUBTITLE@px; font-weight: 600; }
QLabel#EmptyHint { color: @MUTED@; font-size: @FS_LABEL@px; }
QLabel#PhotoTitle { color: @TEXT_SOFT@; font-size: @FS_LABEL@px; font-weight: 500; }
QLabel#PhotoHint { color: @FAINT@; font-size: @FS_CAPTION@px; }
QLabel#PhotoIcon {
    background-color: @SURFACE_SOFT@;
    border: 1px solid @BORDER_SOFT@;
    border-radius: @R_ICON@px;
}
QLabel#Muted { color: @MUTED@; font-size: @FS_LABEL@px; }
QLabel#PopupTitle { color: @TEXT@; font-size: @FS_TITLE@px; font-weight: 600; }
QLabel#PopupSection {
    color: @MUTED@;
    font-size: @FS_CAPTION@px;
    font-weight: 600;
}
QLabel#PopupHint { color: @FAINT@; font-size: @FS_CAPTION@px; }
QCheckBox#LiquidGlass {
    background: @BTN_BG@;
    border: 1px solid @BORDER@;
    border-radius: @R_TAB@px;
    padding: 8px 10px;
    spacing: 8px;
    color: @TEXT@;
    font-weight: 600;
}
QCheckBox#LiquidGlass:hover { background: @BTN_HOVER@; }
QCheckBox#LiquidGlass:checked { background: @CHECKED_BG@; }
QCheckBox#LiquidGlass:focus { border-color: @ACCENT@; }
QCheckBox#LiquidGlass::indicator {
    width: 15px;
    height: 15px;
    background: transparent;
    border: none;
}
QFrame#AccentPreview {
    background: @TOP_STATS_BG@;
    border: 1px solid @ACCENT_BORDER_SOFT@;
    border-radius: @R_ROW@px;
}
QLabel#AccentPreviewDot {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 @ACCENT_GRADIENT_FROM@, stop: 1 @ACCENT_GRADIENT_TO@);
    border: 1px solid @ACCENT_BORDER_SOFT@;
    border-radius: 7px;
}
QLabel#AccentPreviewLabel { color: @MUTED@; font-size: @FS_CAPTION@px; }
QLabel#AccentPreviewValue {
    color: @ACCENT@;
    font-size: @FS_CAPTION@px;
    font-weight: 600;
}

/* -------------------------------------------------------------------- fields */
QLineEdit, QTextEdit, QComboBox, QSpinBox {
    background-color: @INPUT_BG@;
    border: 1px solid @BORDER@;
    border-radius: @R_FIELD@px;
    padding: 9px 12px;
    color: @TEXT@;
    font-size: @FS_BODY@px;
    selection-background-color: @ACCENT@;
    selection-color: @ON_ACCENT@;
}
QLineEdit:hover, QTextEdit:hover, QComboBox:hover, QSpinBox:hover {
    border-color: @BORDER_STRONG@;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid @ACCENT@;
    background-color: @INPUT_FOCUS@;
}
QLineEdit[error="true"], QTextEdit[error="true"] {
    border: 1px solid @LOSS@;
}
QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled {
    color: @FAINT@;
    border-color: @BORDER_SOFT@;
    background-color: @SURFACE_SOFT@;
}
QTextEdit { padding: 9px 11px; }
QComboBox { padding-right: 34px; }
QComboBox::drop-down {
    border: none;
    width: 30px;
}
QComboBox::down-arrow {
    image: url("@CHEVRON@");
    width: 14px;
    height: 14px;
}
QComboBox QAbstractItemView {
    background-color: @PANEL@;
    border: 1px solid @BORDER@;
    border-radius: @R_FIELD@px;
    color: @TEXT@;
    selection-background-color: @SURFACE_HOVER@;
    selection-color: @TEXT@;
    padding: 6px;
    outline: 0;
}
QComboBox QAbstractItemView::item {
    min-height: 28px;
    padding-left: 8px;
    border-radius: @R_CHIP@px;
}

/* ------------------------------------------------------------------- buttons */
QPushButton {
    background: @BTN_BG@;
    border: 1px solid @BORDER@;
    border-radius: @R_BUTTON@px;
    padding: 8px 14px;
    color: @TEXT_SOFT@;
    font-size: @FS_BODY@px;
    font-weight: 500;
}
QPushButton:hover {
    background: @BTN_HOVER@;
    border-color: @ACCENT_BORDER_SOFT@;
    color: @TEXT@;
}
QPushButton:pressed { background-color: @BTN_PRESSED@; }
QPushButton:disabled {
    background-color: transparent;
    border-color: @BORDER_SOFT@;
    color: @FAINT@;
}
QPushButton#Submit, QPushButton#Primary {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 @ACCENT_GRADIENT_FROM@, stop: 1 @ACCENT_GRADIENT_TO@);
    border: 1px solid @SUBMIT_BORDER@;
    border-radius: @R_BUTTON@px;
    padding: 11px;
    font-size: @FS_BODY@px;
    font-weight: 600;
    color: @SUBMIT_TEXT@;
}
QPushButton#Submit:hover, QPushButton#Primary:hover {
    background-color: @SUBMIT_HOVER@;
    border-color: @SUBMIT_BORDER@;
    color: @SUBMIT_TEXT@;
}
QPushButton#Submit:pressed, QPushButton#Primary:pressed {
    background-color: @SUBMIT_PRESSED@;
}
QPushButton#Ghost {
    background-color: transparent;
    border: 1px solid @BORDER_STRONG@;
    border-radius: @R_BUTTON@px;
    padding: 9px 12px;
    color: @MUTED@;
    font-size: @FS_LABEL@px;
}
QPushButton#Ghost:hover {
    background-color: @SURFACE_SOFT@;
    border-color: @BORDER_STRONG@;
    color: @TEXT@;
}
QPushButton#Chip {
    background-color: @CHIP_BG@;
    border: 1px solid @BORDER@;
    border-radius: @R_CHIP@px;
    padding: 5px 10px;
    font-size: @FS_CAPTION@px;
    font-weight: 500;
    color: @TEXT_SOFT@;
}
QPushButton#Chip:hover {
    background-color: @SURFACE@;
    border-color: @ACCENT_BORDER_SOFT@;
    color: @TEXT@;
}
QPushButton#PopupGhost {
    background-color: transparent;
    border: 1px solid @BORDER@;
    border-radius: @R_TAB@px;
    padding: 7px 12px;
    color: @MUTED@;
    font-size: @FS_LABEL@px;
    font-weight: 500;
}
QPushButton#PopupGhost:hover {
    background-color: @SURFACE_SOFT@;
    border-color: @BORDER_STRONG@;
    color: @TEXT@;
}
QPushButton#PopupGhost:checked {
    background-color: @ACCENT_SOFT@;
    border-color: @ACCENT_BORDER_SOFT@;
    color: @ACCENT_TEXT@;
}
QPushButton#PopupGhost:focus { border-color: @ACCENT@; }
QPushButton#PopupGhost:disabled {
    background-color: transparent;
    border-color: @BORDER_SOFT@;
    color: @FAINT@;
}
QPushButton#PopupPrimary {
    background-color: @PRIMARY_BG@;
    border: 1px solid @PRIMARY_BG@;
    border-radius: @R_TAB@px;
    padding: 8px 16px;
    color: @PRIMARY_TEXT@;
    font-size: @FS_LABEL@px;
    font-weight: 600;
}
QPushButton#PopupPrimary:hover { background-color: @PRIMARY_HOVER@; }
QPushButton#Danger {
    background-color: transparent;
    color: @LOSS@;
    border-color: @LOSS_BORDER@;
}
QPushButton#Danger:hover { background-color: @LOSS_TINT@; }

QToolButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: @R_ICON@px;
    padding: 3px;
}
QToolButton:hover {
    background-color: @SURFACE@;
    border-color: @ACCENT_BORDER_SOFT@;
}
QToolButton:pressed { background-color: @SURFACE_HOVER@; }
QToolButton#IconBtn {
    border-radius: @R_ICON@px;
    padding: 0px;
}
QToolButton#IconBtn:hover {
    background-color: @SURFACE@;
    border-color: @ACCENT_BORDER_SOFT@;
}
QToolButton#WinBtn {
    border-radius: @R_ICON@px;
    padding: 0px;
}
QToolButton#WinBtn:hover { background-color: @SURFACE@; }
QToolButton#WinBtn:focus { border-color: @ACCENT@; }
QToolButton#WinClose {
    border-radius: @R_ICON@px;
    padding: 0px;
}
QToolButton#WinClose:hover { background-color: @DANGER@; }
QToolButton#OverlayClose {
    background-color: @OVERLAY_BUTTON_BG@;
    border: 1px solid @OVERLAY_BUTTON_EDGE@;
    border-radius: 16px;
}
QToolButton#OverlayClose:hover { background-color: @OVERLAY_BUTTON_HOVER@; }

/* --------------------------------------------------------------------- photo */
QFrame#PhotoDrop {
    background-color: @INPUT_BG@;
    border: 1px dashed @BORDER_STRONG@;
    border-radius: @R_ROW@px;
}
QFrame#PhotoDrop:hover {
    background-color: @SURFACE_SOFT@;
    border-color: @ACCENT@;
}
QFrame#PhotoDrop[filled="true"] {
    background-color: @SURFACE_SOFT@;
    border: 1px solid @BORDER@;
}

/* --------------------------------------------------------------------- cards */
QFrame#DealCard, QFrame#TransactionCard {
    background: @CARD@;
    border: 1px solid @BORDER_SOFT@;
    border-radius: @R_CARD@px;
}
QFrame#DealCard:hover, QFrame#TransactionCard:hover {
    background: @CARD_HOVER@;
    border-color: @BORDER@;
}
QFrame#DealCard[side="buy"] { border-left: 2px solid @LOSS_BORDER@; }
QFrame#DealCard[side="sell"] { border-left: 2px solid @PROFIT_BORDER@; }
QFrame#DealCard[embedded="true"] {
    background: @EMBED_BG@;
    border: 1px solid @BORDER_SOFT@;
    border-radius: @R_ROW@px;
}
QFrame#DealCard[embedded="true"]:hover {
    background: @EMBED_HOVER@;
    border-color: @BORDER@;
}
QFrame#TransactionCard[side="buy"] {
    background-color: @BUY_BG@;
    border: 1px solid @BUY_BORDER@;
}
QFrame#TransactionCard[side="sell"] {
    background-color: @SELL_BG@;
    border: 1px solid @SELL_BORDER@;
}
QLabel#BadgeBuy, QLabel#Badge {
    background-color: @LOSS_BADGE@;
    color: @LOSS@;
    border: 1px solid @LOSS_BORDER@;
    border-radius: @R_BADGE@px;
    padding: 3px 8px;
    font-size: @FS_MICRO@px;
    font-weight: 600;
}
QLabel#BadgeSell, QLabel#Badge[tone="profit"] {
    background-color: @PROFIT_BADGE@;
    color: @PROFIT@;
    border: 1px solid @PROFIT_BORDER@;
    border-radius: @R_BADGE@px;
    padding: 3px 8px;
    font-size: @FS_MICRO@px;
    font-weight: 600;
}
QLabel#Badge[tone="accent"] {
    background-color: @ACCENT_SOFT@;
    color: @ACCENT_TEXT@;
    border: 1px solid @ACCENT_BORDER_SOFT@;
}
QLabel#Badge[tone="muted"] {
    background-color: @SURFACE_SOFT@;
    color: @MUTED@;
    border: 1px solid @BORDER@;
}
QLabel#AmountBuy { color: @LOSS@; font-size: @FS_SUBTITLE@px; font-weight: 600; }
QLabel#AmountSell { color: @PROFIT@; font-size: @FS_SUBTITLE@px; font-weight: 600; }

/* --------------------------------------------------------------------- total */
QFrame#TotalBar {
    background: @TOTAL_BG@;
    border: 1px solid @BORDER_STRONG@;
    border-radius: @R_CARD@px;
}
QFrame#TotalBar[state="negative"] {
    background-color: @TOTAL_NEG_BG@;
    border: 1px solid @LOSS_BORDER@;
}
QFrame#TotalBar[state="positive"] {
    background-color: @TOTAL_POS_BG@;
    border: 1px solid @PROFIT_BORDER@;
}
QLabel#TotalCaption {
    color: @MUTED@;
    font-size: @FS_BODY@px;
    font-weight: 600;
}
QLabel#TotalValue { color: @TEXT@; font-size: @FS_TITLE@px; font-weight: 700; }
QLabel#TotalValue[state="negative"] { color: @LOSS@; }
QLabel#TotalValue[state="positive"] { color: @PROFIT@; }

/* -------------------------------------------------------------------- market */
QFrame#MarketRow {
    background: @CARD@;
    border: 1px solid @BORDER_SOFT@;
    border-radius: @R_ROW@px;
}
QFrame#MarketRow:hover {
    background: @CARD_HOVER@;
    border-color: @ACCENT_BORDER_SOFT@;
}
QLabel#MarketThumb {
    background-color: @SURFACE_SOFT@;
    border: 1px solid @BORDER_SOFT@;
    border-radius: @R_CHIP@px;
    color: @TEXT_SOFT@;
    font-weight: 600;
}
QLabel#MarketName { color: @TEXT@; font-size: @FS_BODY@px; font-weight: 600; }
QLabel#MarketMeta { color: @FAINT@; font-size: @FS_CAPTION@px; }
QLabel#MarketPrice { color: @TEXT@; font-size: @FS_LABEL@px; font-weight: 600; }
QLabel#MarketSold { color: @FAINT@; font-size: @FS_CAPTION@px; }
QFrame#MarketCard {
    background: @CARD@;
    border: 1px solid @BORDER_SOFT@;
    border-radius: @R_CARD_LARGE@px;
}
QFrame#MarketStat {
    background: @STAT_BG@;
    border: 1px solid @BORDER_SOFT@;
    border-radius: @R_ROW@px;
}
QFrame#MarketStat[highlight="true"] {
    background-color: @ACCENT_SOFT@;
    border-color: @ACCENT_BORDER_SOFT@;
}
QLabel#StatLabel { color: @MUTED@; font-size: @FS_CAPTION@px; }
QLabel#StatValue { color: @TEXT@; font-size: @FS_TITLE@px; font-weight: 700; }
QLabel#StatHint { color: @FAINT@; font-size: @FS_MICRO@px; }
QLabel#MarketTitle { color: @TEXT@; font-size: @FS_TITLE@px; font-weight: 700; }
QLabel#MarketCardTitle { color: @TEXT_SOFT@; font-size: @FS_BODY@px; font-weight: 600; }
QLabel#MarketSub { color: @MUTED@; font-size: @FS_CAPTION@px; }
QLabel#MarketUpdated { color: @FAINT@; font-size: @FS_CAPTION@px; }
QLabel#MarketHint { color: @FAINT@; font-size: @FS_MICRO@px; }
QLabel#MarketStatus { color: @MUTED@; font-size: @FS_LABEL@px; padding: 8px 2px; }
QLabel#MarketStatus[state="error"] { color: @LOSS@; }
QLabel#TableHead { color: @FAINT@; font-size: @FS_MICRO@px; font-weight: 600; }
QLabel#TableCell { color: @MUTED@; font-size: @FS_CAPTION@px; }
QLabel#TableCellStrong { color: @TEXT_SOFT@; font-size: @FS_CAPTION@px; font-weight: 600; }
QLabel#TableCell[state="up"] { color: @PROFIT@; }
QLabel#TableCell[state="down"] { color: @LOSS@; }

/* -------------------------------------------------------------- market trade */
QFrame#TradeCard {
    background: @CARD@;
    border: 1px solid @BORDER@;
    border-radius: @R_CARD_LARGE@px;
}
QPushButton#TradeSide {
    background-color: transparent;
    border: 1px solid @BORDER@;
    border-radius: @R_TAB@px;
    padding: 6px 18px;
    color: @MUTED@;
    font-size: @FS_LABEL@px;
    font-weight: 600;
}
QPushButton#TradeSide:hover {
    background-color: @SURFACE_SOFT@;
    border-color: @BORDER_STRONG@;
    color: @TEXT@;
}
QPushButton#TradeSide:checked {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 @ACCENT_SOFT_STRONG@, stop: 1 @ACCENT_SOFT@);
    border-color: @ACCENT_BORDER_SOFT@;
    color: @ACCENT_TEXT@;
}
QPushButton#TradeQuick {
    background-color: transparent;
    border: 1px solid @BORDER@;
    border-radius: @R_CHIP@px;
    padding: 3px 8px;
    color: @MUTED@;
    font-size: @FS_MICRO@px;
}
QPushButton#TradeQuick:hover {
    background-color: @SURFACE@;
    color: @TEXT@;
}
QPushButton#TradeQuick:disabled {
    color: @FAINT@;
    border-color: @BORDER_SOFT@;
}
QLabel#TradeSum { color: @TEXT@; font-size: @FS_TITLE@px; font-weight: 700; }
QLabel#TradeDelta { color: @MUTED@; font-size: @FS_SUBTITLE@px; font-weight: 700; }
QLabel#TradeDelta[state="good"] { color: @PROFIT@; }
QLabel#TradeDelta[state="bad"] { color: @LOSS@; }
QLabel#TradeVerdict { color: @MUTED@; font-size: @FS_MICRO@px; }
QLabel#TradeOwn { color: @FAINT@; font-size: @FS_MICRO@px; }
QLabel#TradeSaved { color: @PROFIT@; font-size: @FS_CAPTION@px; }
QLabel#TradeSaved[state="error"] { color: @LOSS@; }

/* -------------------------------------------------------------------- scroll */
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollArea > QWidget > QWidget {
    background-color: transparent;
}
QWidget#HistoryContent { background-color: transparent; }
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px 0px;
}
QScrollBar::handle:vertical {
    background: @SCROLL@;
    border-radius: 3px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover { background: @ACCENT_LIGHT@; }
QScrollArea#MarketDetailScroll QScrollBar::handle:vertical:disabled {
    background: transparent;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
QScrollBar:horizontal { height: 0px; }

/* ----------------------------------------------------------- calendar popup */
QFrame#PopupCard {
    background: @POPUP_MATERIAL@;
    border: 1px solid @PANEL_EDGE@;
    border-radius: @R_POPUP@px;
}
QCalendarWidget QWidget {
    background-color: @CAL_BG@;
    color: @TEXT@;
}
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: @CAL_BG@;
    border-bottom: 1px solid @BORDER_SOFT@;
}
QCalendarWidget QToolButton {
    background-color: transparent;
    border: none;
    border-radius: @R_CHIP@px;
    color: @TEXT@;
    font-size: @FS_LABEL@px;
    font-weight: 600;
    padding: 4px 8px;
}
QCalendarWidget QToolButton:hover { background-color: @SURFACE@; }
QCalendarWidget QToolButton::menu-indicator { image: none; }
QCalendarWidget QMenu {
    background-color: @PANEL@;
    border: 1px solid @BORDER@;
    color: @TEXT@;
}
QCalendarWidget QMenu::item:selected { background-color: @SURFACE@; }
QCalendarWidget QSpinBox {
    background-color: @INPUT_BG@;
    color: @TEXT@;
    border: 1px solid @BORDER@;
    selection-background-color: @ACCENT@;
}
QCalendarWidget QAbstractItemView:enabled {
    background-color: @CAL_BG@;
    alternate-background-color: @CAL_ALT@;
    color: @TEXT_SOFT@;
    selection-background-color: @ACCENT@;
    selection-color: @ON_ACCENT@;
    outline: 0;
    border: none;
    font-size: @FS_LABEL@px;
}
QCalendarWidget QAbstractItemView:disabled { color: @FAINT@; }
QCalendarWidget QTableView {
    background-color: @CAL_BG@;
    alternate-background-color: @CAL_ALT@;
    selection-background-color: @ACCENT@;
    selection-color: @ON_ACCENT@;
    border: none;
}
QCalendarWidget QHeaderView {
    background-color: @CAL_BG@;
    color: @MUTED@;
    border: none;
}
QCalendarWidget QHeaderView::section {
    background-color: @CAL_BG@;
    color: @MUTED@;
    border: none;
    padding: 3px 0px;
    font-size: @FS_CAPTION@px;
}
QLineEdit#TimeSpin {
    min-height: 20px;
    padding: 0px 4px;
    font-size: @FS_BODY@px;
    background-color: @INPUT_BG@;
}

/* ---------------------------------------------------------------------- misc */
QToolTip {
    background-color: @PANEL@;
    color: @TEXT@;
    border: 1px solid @BORDER@;
    border-radius: @R_CHIP@px;
    padding: 6px 9px;
}
QLabel#Toast {
    background: @TOAST_BG@;
    border: 1px solid @BORDER@;
    border-radius: @R_HEADER@px;
    padding: 9px 16px;
    color: @TEXT@;
    font-size: @FS_LABEL@px;
}
QMessageBox {
    background: @DIALOG_BG@;
}
QMessageBox QLabel {
    color: @TEXT@;
    font-size: @FS_BODY@px;
    min-width: 300px;
}
QMessageBox QPushButton { min-width: 84px; }
QWidget#ImageOverlay { background-color: @OVERLAY@; }
QLabel#OverlayHint { color: @OVERLAY_HINT@; font-size: @FS_LABEL@px; }
QLabel#OverlayTitle { color: @OVERLAY_TEXT@; font-size: @FS_SUBTITLE@px; font-weight: 600; }
QSizeGrip { background-color: transparent; }
"""

LIQUID_GLASS_QSS = r"""
QPushButton#Tab:focus, QPushButton#Ghost:focus,
QPushButton#TradeSide:focus, QPushButton#TradeQuick:focus,
QToolButton#IconBtn:focus {
    border-color: @ACCENT@;
}
QLineEdit, QTextEdit { placeholder-text-color: @FAINT@; }
"""

# Backwards-compatible aliases: old code exposed the raw QSS blocks.
BASE_QSS = QSS_TEMPLATE
LIGHT_QSS = ""


# ------------------------------------------------------------------ utilities
def set_active_theme(theme_name: str, *, liquid_glass: bool = False) -> str:
    """Remember the theme so widgets can pick readable icon colours."""
    global _ACTIVE_THEME, _ACTIVE_LIQUID_GLASS
    _ACTIVE_THEME = theme_name if theme_name in THEMES else DEFAULT_THEME
    _ACTIVE_LIQUID_GLASS = liquid_glass
    return _ACTIVE_THEME


def active_theme() -> str:
    return _ACTIVE_THEME


def active_liquid_glass() -> bool:
    return _ACTIVE_LIQUID_GLASS


def icon_tone(role: str = "muted") -> str:
    """Icon colour that stays readable in either theme."""
    colors = design.tokens(_ACTIVE_THEME, liquid_glass=_ACTIVE_LIQUID_GLASS)
    tones = {
        "muted": colors.muted,
        "text": colors.text,
        "strong": colors.text_soft,
        "faint": colors.faint,
    }
    return tones.get(role, colors.muted)


# -------------------------------------------------------------- colour helpers
def accent_profile(
    accent: str, theme_name: str = DEFAULT_THEME
) -> design.AccentProfile:
    """Full derived accent palette (base, tones, glow, gradient, contrast)."""
    return design.accent_profile(accent, theme_name)


def theme_accent(accent: str, theme_name: str = DEFAULT_THEME) -> QColor:
    """Accent used for painting: always readable on the theme background."""
    return QColor(accent_profile(accent, theme_name).base)


def glass_washes(accent: str, theme_name: str) -> tuple[QColor, QColor]:
    primary = theme_accent(accent, theme_name)
    reflection = design.blend(primary, design.GLASS_REFLECTION, 0.65)
    light = theme_name == "light"
    colors = design.tokens(theme_name, liquid_glass=True)
    for wash, opacity in (
        (primary, 0.28 if light else 0.46),
        (reflection, 0.25 if light else 0.42),
    ):
        # Keep title-bar text readable with unusually bright or dark accents.
        while design.contrast_ratio(
            design.blend(colors.bg, wash, opacity), colors.muted
        ) < 4.5:
            opacity *= 0.90
        wash.setAlphaF(opacity)
    return primary, reflection


def shadow_color(
    theme_name: str = DEFAULT_THEME,
    accent: str = DEFAULT_ACCENT,
    *,
    strong: bool = True,
) -> QColor:
    """Theme-specific elevation shadow, very lightly tinted by the accent."""
    tokens = design.tokens(theme_name)
    base = QColor(tokens.shadow if strong else tokens.shadow_soft)
    if not base.isValid():
        base = QColor(0, 0, 0, 150)
    tint = 0.16 if theme_name != "light" else 0.09
    result = design.blend(base, theme_accent(accent, theme_name), tint)
    result.setAlpha(base.alpha())
    return result


def relative_luminance(color: str | QColor) -> float:
    return design.relative_luminance(color)


def contrast_ratio(first: str | QColor, second: str | QColor) -> float:
    return design.contrast_ratio(first, second)


def contrast_text(background: str | QColor) -> QColor:
    """White or near-black text, whichever reads better on the background."""
    return design.contrast_text(background)


def _blend(color: QColor, target: QColor, amount: float) -> QColor:
    return design.blend(color, target, amount)


def _ensure_contrast(
    color: QColor, background: QColor, toward_white: bool, minimum: float = 4.5
) -> QColor:
    return design.ensure_contrast(color, background, toward_white, minimum)


# ---------------------------------------------------------------------- tokens
def _qss_tokens(
    theme_name: str, accent: str, *, liquid_glass: bool = False
) -> dict[str, str]:
    """Map semantic design tokens to the placeholders used by the QSS."""
    theme = design.tokens(theme_name, liquid_glass=liquid_glass)
    profile = accent_profile(accent, theme_name)
    accent_color = QColor(profile.base)
    light = theme_name == "light"
    on_accent = QColor(profile.on)
    radius = design.RADIUS

    # Accent-driven surfaces -------------------------------------------------
    accent_soft = profile.soft
    accent_soft_strong = profile.soft_strong
    accent_border_soft = profile.border
    input_focus = design.mix(
        theme.input_bg, accent_color, 0.035 if light else 0.045
    )
    panel_glow = design.mix(
        theme.panel_top, accent_color, 0.035 if light else 0.07
    )
    accent_surface = design.mix(
        theme.panel, accent_color, 0.24 if light else 0.28
    )
    accent_text = design.ensure_contrast(
        accent_color, accent_surface, toward_white=not light, minimum=4.5
    ).name()

    submit_bg = profile.base
    submit_hover = profile.hover
    submit_pressed = profile.pressed
    submit_border = profile.base
    submit_text = profile.on

    if light:
        primary_bg = theme.text
        primary_hover = design.mix(theme.text, "#000000", 0.16)
        primary_text = "#FFFFFF"
    else:
        primary_bg = theme.text
        primary_hover = "#FFFFFF"
        primary_text = theme.bg

    # Neutral surfaces -------------------------------------------------------
    surface_soft = design.rgba(theme.surface, 0.55 if not light else 0.75)
    surface_translucent = design.rgba(theme.surface, 0.75 if not light else 0.85)
    header_bg = design.mix(theme.panel, theme.surface, 0.30 if not light else 0.55)
    header_hover = design.mix(
        theme.panel, theme.surface_hover, 0.42 if not light else 0.78
    )
    pair_bg = design.mix(theme.panel, theme.surface, 0.46 if not light else 0.70)
    pair_hover = design.mix(
        theme.panel, theme.surface_hover, 0.58 if not light else 0.88
    )
    pill_bg = design.mix(theme.panel, theme.surface, 0.50 if not light else 0.72)
    chip_bg = design.rgba(theme.surface, 0.45 if not light else 0.65)
    btn_bg = design.mix(theme.panel, theme.surface, 0.55 if not light else 0.80)
    btn_hover = design.mix(theme.panel, theme.surface_hover, 0.72 if not light else 0.95)
    btn_pressed = design.mix(theme.panel, theme.surface, 0.38 if not light else 0.70)
    stat_bg = design.mix(theme.card, theme.surface, 0.35 if not light else 0.45)
    toast_bg = design.mix(theme.panel, theme.surface, 0.62 if not light else 0.10)
    cal_alt = theme.bg_bottom if light else design.mix(theme.panel, theme.surface, 0.30)
    scroll = design.mix(theme.panel, theme.border_strong, 0.72)

    # Financial semantics ----------------------------------------------------
    profit, loss = theme.profit, theme.loss
    buy_bg = design.mix(theme.card, loss, 0.10 if not light else 0.06)
    buy_hover = design.mix(theme.card, loss, 0.15 if not light else 0.10)
    buy_border = design.rgba(loss, 0.30 if not light else 0.32)
    sell_bg = design.mix(theme.card, profit, 0.09 if not light else 0.06)
    sell_hover = design.mix(theme.card, profit, 0.14 if not light else 0.10)
    sell_border = design.rgba(profit, 0.26 if not light else 0.28)
    loss_tint = design.rgba(loss, 0.12 if not light else 0.10)
    profit_tint = design.rgba(profit, 0.12 if not light else 0.10)
    loss_border = design.rgba(loss, 0.45 if not light else 0.40)
    profit_border = design.rgba(profit, 0.42 if not light else 0.38)
    loss_badge = design.rgba(loss, 0.16 if not light else 0.12)
    profit_badge = design.rgba(profit, 0.15 if not light else 0.12)
    total_bg = design.mix(theme.panel, theme.surface, 0.34 if not light else 0.52)
    total_neg = design.mix(theme.panel, loss, 0.12 if not light else 0.07)
    total_pos = design.mix(theme.panel, profit, 0.10 if not light else 0.07)
    embed_bg = design.mix(theme.card, theme.bg, 0.30 if not light else 0.18)
    embed_hover = design.mix(theme.card, theme.surface_hover, 0.45 if not light else 0.55)

    tokens = {
        "FONT": design.font_family(),
        # type scale
        "FS_MICRO": str(design.TYPE_SCALE["micro"][0]),
        "FS_CAPTION": str(design.TYPE_SCALE["caption"][0]),
        "FS_LABEL": str(design.TYPE_SCALE["label"][0]),
        "FS_BODY": str(design.TYPE_SCALE["body"][0]),
        "FS_SUBTITLE": str(design.TYPE_SCALE["subtitle"][0]),
        "FS_TITLE": str(design.TYPE_SCALE["title"][0]),
        "FS_DISPLAY": str(design.TYPE_SCALE["display"][0]),
        # radii
        "R_PANEL": str(radius["panel"]),
        "R_POPUP": str(radius["popup"]),
        "R_CARD": str(radius["card"]),
        "R_CARD_LARGE": str(radius["card_large"]),
        "R_ROW": str(radius["row"]),
        "R_HEADER": str(radius["header"]),
        "R_FIELD": str(radius["field"]),
        "R_BUTTON": str(radius["button"]),
        "R_TAB": str(radius["tab"]),
        "R_CHIP": str(radius["chip"]),
        "R_ICON": str(radius["icon"]),
        "R_BADGE": str(radius["badge"]),
        # colours
        "BG": theme.bg,
        "PANEL": theme.panel,
        "CARD": theme.card,
        "CARD_HOVER": theme.card_hover,
        "SURFACE": theme.surface,
        "SURFACE_HOVER": theme.surface_hover,
        "SURFACE_SOFT": surface_soft,
        "INPUT_BG": theme.input_bg,
        "INPUT_FOCUS": input_focus,
        "BORDER": theme.border,
        "BORDER_SOFT": theme.border_soft,
        "BORDER_STRONG": theme.border_strong,
        "TEXT": theme.text,
        "TEXT_SOFT": theme.text_soft,
        "MUTED": theme.muted,
        "FAINT": theme.faint,
        "PROFIT": profit,
        "LOSS": loss,
        "DANGER": design.DANGER,
        "OVERLAY": theme.overlay,
        "OVERLAY_TEXT": theme.text,
        "OVERLAY_HINT": theme.muted,
        "OVERLAY_BUTTON_BG": surface_translucent,
        "OVERLAY_BUTTON_HOVER": theme.surface_hover,
        "OVERLAY_BUTTON_EDGE": theme.border,
        # accent
        "ACCENT": profile.base,
        "ACCENT_LIGHT": profile.light,
        "ACCENT_DARK": profile.dark,
        "ACCENT_SOFT": accent_soft,
        "ACCENT_SOFT_STRONG": accent_soft_strong,
        "ACCENT_BORDER_SOFT": accent_border_soft,
        "ACCENT_GLOW": profile.glow,
        "ACCENT_GRADIENT_FROM": profile.gradient_from,
        "ACCENT_GRADIENT_TO": profile.gradient_to,
        "ACCENT_STRONG": profile.dark,
        "ACCENT_TEXT": accent_text,
        "PANEL_MATERIAL": (
            "qlineargradient(x1: 0, y1: 0, x2: 0.3, y2: 1, "
            f"stop: 0 {panel_glow}, stop: 0.62 {theme.panel_top}, stop: 1 {theme.panel})"
        ),
        "POPUP_MATERIAL": (
            "qlineargradient(x1: 0, y1: 0, x2: 0.6, y2: 1, "
            f"stop: 0 {panel_glow}, stop: 0.5 {theme.panel}, stop: 1 {theme.panel})"
        ),
        "PANEL_EDGE": theme.border,
        "DIALOG_BG": theme.panel,
        "CAL_BG": theme.panel,
        "ON_ACCENT": on_accent.name(),
        "CHEVRON": "@CHEVRON@",
        # component surfaces
        "HEADER_BG": header_bg,
        "HEADER_HOVER": header_hover,
        "PAIR_BG": pair_bg,
        "PAIR_HOVER": pair_hover,
        "PILL_BG": pill_bg,
        "TOP_STATS_BG": surface_soft,
        "CHIP_BG": chip_bg,
        "CHECKED_BG": accent_soft,
        "TAB_ACTIVE_BG": accent_soft,
        "TAB_ACTIVE_BORDER": accent_border_soft,
        "BTN_BG": btn_bg,
        "BTN_HOVER": btn_hover,
        "BTN_PRESSED": btn_pressed,
        "SUBMIT_BG": submit_bg,
        "SUBMIT_HOVER": submit_hover,
        "SUBMIT_PRESSED": submit_pressed,
        "SUBMIT_BORDER": submit_border,
        "SUBMIT_TEXT": submit_text,
        "PRIMARY_BG": primary_bg,
        "PRIMARY_HOVER": primary_hover,
        "PRIMARY_TEXT": primary_text,
        "STAT_BG": stat_bg,
        "TOAST_BG": toast_bg,
        "CAL_ALT": cal_alt,
        "SCROLL": scroll,
        "BUY_BG": buy_bg,
        "BUY_HOVER": buy_hover,
        "BUY_BORDER": buy_border,
        "SELL_BG": sell_bg,
        "SELL_HOVER": sell_hover,
        "SELL_BORDER": sell_border,
        "LOSS_TINT": loss_tint,
        "PROFIT_TINT": profit_tint,
        "LOSS_BORDER": loss_border,
        "PROFIT_BORDER": profit_border,
        "LOSS_BADGE": loss_badge,
        "PROFIT_BADGE": profit_badge,
        "TOTAL_BG": total_bg,
        "TOTAL_NEG_BG": total_neg,
        "TOTAL_POS_BG": total_pos,
        "EMBED_BG": embed_bg,
        "EMBED_HOVER": embed_hover,
    }
    if liquid_glass:
        tokens.update(_glass_materials(theme, accent_color, tokens))
    return tokens


def _material(top: str, bottom: str) -> str:
    return (
        "qlineargradient(x1: 0, y1: 0, x2: 0.35, y2: 1, "
        f"stop: 0 {top}, stop: 1 {bottom})"
    )


def _glass_materials(
    colors: design.Theme, accent: QColor, tokens: dict[str, str]
) -> dict[str, str]:
    light = colors.name == "light"
    mix, rgba = design.mix, design.rgba
    glint = mix(accent, "#FFFFFF", 0.82)
    edge = rgba(accent, 0.32 if light else 0.43)
    panel_top = mix(colors.panel, accent, 0.08 if light else 0.27)
    panel_bottom = mix(colors.panel, accent, 0.025 if light else 0.10)
    popup_top = mix(colors.panel, accent, 0.15 if light else 0.26)
    card_top = mix(colors.card, glint, 0.55 if light else 0.17)
    card_bottom = mix(colors.card, accent, 0.07 if light else 0.09)
    card = _material(rgba(card_top, 0.80), rgba(card_bottom, 0.53 if light else 0.46))
    inset = _material(
        rgba(colors.input_bg, 0.70), rgba(card_bottom, 0.57 if light else 0.43)
    )
    raised = _material(
        rgba(glint if light else card_top, 0.68),
        rgba(card_bottom, 0.60),
    )
    soft = rgba(card_top, 0.40)
    thin_edge = rgba(accent, 0.19 if light else 0.23)
    overlay_tint = mix(design.DARK.bg, accent, 0.12)
    return {
        "PANEL_MATERIAL": _material(
            rgba(panel_top, 0.48 if light else 0.36),
            rgba(panel_bottom, 0.62 if light else 0.48),
        ),
        "POPUP_MATERIAL": _material(rgba(popup_top, 0.97), rgba(panel_bottom, 0.98)),
        "PANEL_EDGE": _material(rgba(glint, 0.96 if light else 0.52), edge),
        "DIALOG_BG": _material(popup_top, panel_bottom),
        "PANEL": panel_bottom,
        "BORDER": rgba(accent, 0.26 if light else 0.37),
        "BORDER_SOFT": thin_edge,
        "BORDER_STRONG": edge,
        "CARD": card,
        # Animated cards blend a tint over these resting materials.
        "CARD_HOVER": card,
        "EMBED_BG": inset,
        "EMBED_HOVER": inset,
        "HEADER_BG": raised,
        "HEADER_HOVER": raised,
        "PAIR_BG": card,
        "INPUT_BG": rgba(colors.input_bg, 0.72 if light else 0.64),
        "INPUT_FOCUS": rgba(tokens["INPUT_FOCUS"], 0.88),
        "SURFACE": rgba(card_top, 0.67),
        "SURFACE_HOVER": rgba(mix(card_top, accent, 0.25), 0.65),
        "SURFACE_SOFT": soft,
        "PILL_BG": raised,
        "TOP_STATS_BG": raised,
        "CHIP_BG": soft,
        "BTN_BG": raised,
        "BTN_HOVER": _material(rgba(glint, 0.53 if light else 0.25), soft),
        "BTN_PRESSED": rgba(accent, 0.22),
        "CHECKED_BG": _material(tokens["ACCENT_SOFT_STRONG"], tokens["ACCENT_SOFT"]),
        "STAT_BG": raised,
        "TOTAL_BG": raised,
        "TOTAL_NEG_BG": rgba(mix(colors.panel, colors.loss, 0.13), 0.73),
        "TOTAL_POS_BG": rgba(mix(colors.panel, colors.profit, 0.12), 0.73),
        "BUY_BG": rgba(tokens["BUY_BG"], 0.75),
        "SELL_BG": rgba(tokens["SELL_BG"], 0.75),
        "CAL_BG": mix(colors.panel, accent, 0.08 if light else 0.15),
        "CAL_ALT": mix(colors.panel, accent, 0.11 if light else 0.18),
        "TOAST_BG": _material(rgba(popup_top, 0.98), rgba(panel_bottom, 0.98)),
        "SCROLL": edge,
        "OVERLAY": rgba(overlay_tint, 0.92),
        "OVERLAY_TEXT": design.DARK.text,
        "OVERLAY_HINT": design.DARK.text_soft,
        "OVERLAY_BUTTON_BG": rgba(glint, 0.14),
        "OVERLAY_BUTTON_HOVER": rgba(glint, 0.25),
        "OVERLAY_BUTTON_EDGE": rgba(glint, 0.35),
    }


def palette(
    theme_name: str = DEFAULT_THEME,
    accent: str = DEFAULT_ACCENT,
    *,
    liquid_glass: bool = False,
) -> QPalette:
    highlight = theme_accent(accent, theme_name)
    theme = design.tokens(theme_name, liquid_glass=liquid_glass)
    result = QPalette()
    roles = {
        QPalette.ColorRole.Window: theme.bg,
        QPalette.ColorRole.WindowText: theme.text,
        QPalette.ColorRole.Base: theme.input_bg,
        QPalette.ColorRole.AlternateBase: theme.surface,
        QPalette.ColorRole.Text: theme.text,
        QPalette.ColorRole.Button: theme.surface,
        QPalette.ColorRole.ButtonText: theme.text,
        QPalette.ColorRole.PlaceholderText: theme.faint,
        QPalette.ColorRole.ToolTipBase: theme.panel,
        QPalette.ColorRole.ToolTipText: theme.text,
    }
    for role, color in roles.items():
        result.setColor(role, QColor(color))
    result.setColor(QPalette.ColorRole.Highlight, highlight)
    result.setColor(QPalette.ColorRole.HighlightedText, contrast_text(highlight))
    result.setColor(QPalette.ColorRole.Link, highlight)
    return result


def stylesheet(
    chevron_path: str,
    accent: str = DEFAULT_ACCENT,
    theme_name: str = DEFAULT_THEME,
    *,
    liquid_glass: bool = False,
) -> str:
    tokens = _qss_tokens(theme_name, accent, liquid_glass=liquid_glass)
    tokens["CHEVRON"] = chevron_path.replace("\\", "/")

    def replace(match: re.Match[str]) -> str:
        return tokens.get(match.group(1), match.group(0))

    template = QSS_TEMPLATE + LIQUID_GLASS_QSS if liquid_glass else QSS_TEMPLATE
    return re.sub(r"@([A-Z0-9_]+)@", replace, template)
