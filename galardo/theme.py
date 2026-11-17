from __future__ import annotations

from PySide6.QtGui import QColor, QPalette

BASE_QSS = r"""
QWidget {
    color: #E7E9EC;
    font-family: "Segoe UI";
    font-size: 13px;
}
QLabel {
    background-color: transparent;
}

/* ------------------------------------------------------------------ panels */
QFrame#Panel {
    background-color: rgba(9, 10, 12, 188);
    border: 1px solid rgba(255, 255, 255, 20);
    border-radius: 14px;
}
QLabel#FieldLabel {
    color: #878D96;
    font-size: 12px;
}
QLabel#AppTitle {
    color: #F4F5F7;
    font-size: 15px;
    font-weight: 600;
}
QLabel#HistoryPill {
    background-color: rgba(255, 255, 255, 7);
    border: 1px solid rgba(255, 255, 255, 24);
    border-radius: 8px;
    padding: 7px 14px;
    color: #ECEFF2;
    font-size: 12px;
    font-weight: 600;
}
QLabel#CountMuted {
    color: #6C727B;
    font-size: 11px;
}
QPushButton#Tab {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 6px 11px;
    color: #868C95;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#Tab:hover {
    background-color: rgba(255, 255, 255, 6);
    color: #E7E9EC;
}
QPushButton#Tab:checked {
    background-color: rgba(255, 255, 255, 9);
    border-color: rgba(255, 255, 255, 26);
    color: #F2F4F6;
}
QFrame#WeekHeader {
    background-color: rgba(255, 255, 255, 4);
    border: 1px solid rgba(255, 255, 255, 11);
    border-radius: 8px;
}
QFrame#WeekHeader:hover {
    background-color: rgba(255, 255, 255, 8);
}
QLabel#WeekChevron {
    color: #8C929A;
    font-size: 11px;
}
QLabel#WeekTitle {
    color: #C6CBD2;
    font-size: 12px;
    font-weight: 600;
}
QLabel#WeekMeta {
    color: #6B717A;
    font-size: 11px;
}
QLabel#WeekAmount {
    color: #A6ABB3;
    font-size: 12px;
    font-weight: 600;
}
QLabel#DragHandle {
    background-color: transparent;
    border-radius: 4px;
}
QLabel#DragHandle:hover {
    background-color: rgba(255, 255, 255, 14);
}
QFrame#PairHeader {
    background-color: rgba(255, 255, 255, 6);
    border: 1px solid rgba(255, 255, 255, 18);
    border-radius: 8px;
}
QFrame#PairHeader:hover {
    background-color: rgba(255, 255, 255, 11);
}
QLabel#PairChevron {
    color: #8C929A;
    font-size: 11px;
}
QLabel#PairTitle {
    color: #F1F3F5;
    font-size: 13px;
    font-weight: 600;
}
QLabel#PairMeta {
    color: #8A9099;
    font-size: 11px;
}
QLabel#PairProfit {
    color: #A6ABB3;
    font-size: 12px;
    font-weight: 600;
}
QLabel#PairProfit[state="positive"] {
    color: #67E396;
}
QLabel#PairProfit[state="negative"] {
    color: #FF8D8D;
}
QFrame#DropLine {
    background-color: @ACCENT@;
    border: none;
    border-radius: 1px;
}
QLabel#DealTitle {
    color: #F1F3F5;
    font-size: 14px;
    font-weight: 600;
}
QLabel#DealDate {
    color: #6B717A;
    font-size: 13px;
}
QLabel#DealComment {
    color: #A6ABB3;
    font-size: 12px;
    font-style: italic;
}
QLabel#EmptyTitle {
    color: #D5D8DD;
    font-size: 14px;
    font-weight: 600;
}
QLabel#EmptyHint {
    color: #6C727B;
    font-size: 12px;
}
QLabel#PhotoTitle {
    color: #D9DCE1;
    font-size: 12px;
}
QLabel#PhotoHint {
    color: #6D737C;
    font-size: 11px;
}
QLabel#PhotoIcon {
    background-color: rgba(255, 255, 255, 7);
    border: 1px solid rgba(255, 255, 255, 12);
    border-radius: 10px;
}
QLabel#Muted {
    color: #7B818A;
    font-size: 12px;
}
QLabel#PopupTitle {
    color: #F1F3F5;
    font-size: 14px;
    font-weight: 600;
}
QLabel#PopupSection {
    color: #878D96;
    font-size: 11px;
    font-weight: 600;
}
QLabel#PopupHint {
    color: #6C727B;
    font-size: 11px;
}

/* ------------------------------------------------------------------ inputs */
QLineEdit, QTextEdit, QComboBox, QSpinBox {
    background-color: rgba(13, 15, 19, 208);
    border: 1px solid #2E333A;
    border-radius: 9px;
    padding: 8px 11px;
    color: #E9EBEE;
    font-size: 13px;
    selection-background-color: @ACCENT@;
    selection-color: @ON_ACCENT@;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid @ACCENT@;
    background-color: rgba(17, 20, 25, 228);
}
QLineEdit[error="true"], QTextEdit[error="true"] {
    border: 1px solid #D95C5C;
}
QTextEdit {
    padding: 8px 10px;
}
QComboBox {
    padding-right: 32px;
}
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
    background-color: #14171B;
    border: 1px solid #2D3239;
    border-radius: 8px;
    color: #E9EBEE;
    selection-background-color: #242B36;
    selection-color: #FFFFFF;
    padding: 5px;
    outline: 0;
}
QComboBox QAbstractItemView::item {
    min-height: 26px;
    padding-left: 7px;
}

/* ----------------------------------------------------------------- buttons */
QPushButton {
    background-color: #1A1D22;
    border: 1px solid #2E333A;
    border-radius: 8px;
    padding: 8px 14px;
    color: #E9EBEE;
}
QPushButton:hover {
    background-color: #23272D;
}
QPushButton:pressed {
    background-color: #171A1E;
}
QPushButton#Submit {
    background-color: @ACCENT_SOFT@;
    border: 1px solid @ACCENT@;
    border-radius: 9px;
    padding: 11px;
    font-size: 13px;
    font-weight: 600;
    color: #F2F4F6;
}
QPushButton#Submit:hover {
    background-color: @ACCENT_SOFT_STRONG@;
    border-color: @ACCENT@;
}
QPushButton#Submit:pressed {
    background-color: @ACCENT_SOFT@;
}
QPushButton#Ghost {
    background-color: transparent;
    border: 1px solid rgba(255, 255, 255, 26);
    border-radius: 8px;
    padding: 9px 12px;
    color: #B9BEC6;
    font-size: 12px;
}
QPushButton#Ghost:hover {
    background-color: rgba(255, 255, 255, 7);
    color: #E9EBEE;
}
QPushButton#Chip {
    background-color: rgba(8, 9, 11, 80);
    border: 1px solid rgba(255, 255, 255, 29);
    border-radius: 7px;
    padding: 5px 10px;
    font-size: 11px;
    color: #D5D9DE;
}
QPushButton#Chip:hover {
    background-color: rgba(255, 255, 255, 11);
    border-color: rgba(255, 255, 255, 48);
}
QPushButton#PopupGhost {
    background-color: transparent;
    border: 1px solid rgba(255, 255, 255, 24);
    border-radius: 8px;
    padding: 7px 12px;
    color: #B9BEC6;
    font-size: 12px;
}
QPushButton#PopupGhost:hover {
    background-color: rgba(255, 255, 255, 7);
}
QPushButton#PopupGhost:checked {
    background-color: rgba(255, 255, 255, 13);
    border-color: rgba(255, 255, 255, 72);
    color: #F3F5F7;
}
QPushButton#PopupPrimary {
    background-color: #EDEFF2;
    border: 1px solid #EDEFF2;
    border-radius: 8px;
    padding: 7px 16px;
    color: #101215;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#PopupPrimary:hover {
    background-color: #FFFFFF;
}
QPushButton#Danger {
    color: #FF9C9C;
    border-color: rgba(214, 92, 92, 90);
}
QPushButton#Danger:hover {
    background-color: rgba(214, 92, 92, 40);
}

QToolButton {
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 3px;
}
QToolButton:hover {
    background-color: rgba(255, 255, 255, 13);
}
QToolButton:pressed {
    background-color: rgba(255, 255, 255, 7);
}
QToolButton#WinBtn {
    border-radius: 7px;
    padding: 0px;
}
QToolButton#WinBtn:hover {
    background-color: rgba(255, 255, 255, 14);
}
QToolButton#WinClose {
    border-radius: 7px;
    padding: 0px;
}
QToolButton#WinClose:hover {
    background-color: #D94147;
}
QToolButton#OverlayClose {
    background-color: rgba(255, 255, 255, 18);
    border: 1px solid rgba(255, 255, 255, 30);
    border-radius: 16px;
}
QToolButton#OverlayClose:hover {
    background-color: rgba(255, 255, 255, 30);
}

/* ------------------------------------------------------------------ photo */
QFrame#PhotoDrop {
    background-color: rgba(255, 255, 255, 3);
    border: 1px solid #30363D;
    border-radius: 10px;
}
QFrame#PhotoDrop:hover {
    background-color: rgba(255, 255, 255, 6);
    border-color: #4A525C;
}
QFrame#PhotoDrop[filled="true"] {
    background-color: rgba(255, 255, 255, 5);
    border: 1px solid #30363D;
}

/* ------------------------------------------------------------------ cards */
QFrame#DealCard {
    border-radius: 10px;
}
QFrame#DealCard[side="buy"] {
    background-color: rgba(82, 32, 34, 140);
    border: 1px solid rgba(211, 94, 94, 46);
}
QFrame#DealCard[side="buy"]:hover {
    background-color: rgba(92, 38, 40, 166);
}
QFrame#DealCard[side="sell"] {
    background-color: rgba(25, 62, 41, 140);
    border: 1px solid rgba(86, 191, 122, 42);
}
QFrame#DealCard[side="sell"]:hover {
    background-color: rgba(30, 72, 48, 166);
}
QLabel#BadgeBuy {
    background-color: rgba(255, 110, 110, 34);
    color: #FF9D9D;
    border-radius: 5px;
    padding: 3px 7px;
    font-size: 11px;
    font-weight: 600;
}
QLabel#BadgeSell {
    background-color: rgba(95, 224, 145, 32);
    color: #72E6A0;
    border-radius: 5px;
    padding: 3px 7px;
    font-size: 11px;
    font-weight: 600;
}
QLabel#AmountBuy {
    color: #FF8D8D;
    font-size: 14px;
    font-weight: 600;
}
QLabel#AmountSell {
    color: #67E396;
    font-size: 14px;
    font-weight: 600;
}

/* ------------------------------------------------------------------- total */
QFrame#TotalBar {
    background-color: rgba(255, 255, 255, 4);
    border: 1px solid rgba(255, 255, 255, 14);
    border-radius: 10px;
}
QFrame#TotalBar[state="negative"] {
    background-color: rgba(92, 33, 35, 150);
    border: 1px solid rgba(214, 92, 92, 52);
}
QFrame#TotalBar[state="positive"] {
    background-color: rgba(26, 68, 44, 150);
    border: 1px solid rgba(86, 191, 122, 44);
}
QLabel#TotalCaption {
    color: #C4C8CE;
    font-size: 12px;
    font-weight: 600;
}
QLabel#TotalValue {
    color: #D9DCE1;
    font-size: 15px;
    font-weight: 700;
}
QLabel#TotalValue[state="negative"] {
    color: #FF8D8D;
}
QLabel#TotalValue[state="positive"] {
    color: #67E396;
}

/* ------------------------------------------------------------------ market */
QFrame#MarketRow {
    background-color: rgba(255, 255, 255, 4);
    border: 1px solid rgba(255, 255, 255, 8);
    border-radius: 10px;
}
QFrame#MarketRow:hover {
    background-color: rgba(255, 255, 255, 9);
    border-color: rgba(255, 255, 255, 22);
}
QLabel#MarketThumb {
    background-color: rgba(255, 255, 255, 6);
    border: 1px solid rgba(255, 255, 255, 12);
    border-radius: 9px;
    color: #C6CBD2;
    font-weight: 600;
}
QLabel#MarketName { color: #E9EBEE; font-size: 13px; font-weight: 600; }
QLabel#MarketMeta { color: #6C727B; font-size: 11px; }
QLabel#MarketPrice { color: #E9EBEE; font-size: 12px; font-weight: 600; }
QLabel#MarketSold { color: #6C727B; font-size: 11px; }
QFrame#MarketCard {
    background-color: rgba(255, 255, 255, 3);
    border: 1px solid rgba(255, 255, 255, 12);
    border-radius: 12px;
}
QFrame#MarketStat {
    background-color: rgba(255, 255, 255, 4);
    border: 1px solid rgba(255, 255, 255, 12);
    border-radius: 10px;
}
QFrame#MarketStat[highlight="true"] {
    background-color: @ACCENT_SOFT@;
    border-color: @ACCENT@;
}
QLabel#StatLabel { color: #7B818A; font-size: 11px; }
QLabel#StatValue { color: #F1F3F5; font-size: 16px; font-weight: 700; }
QLabel#StatHint { color: #6C727B; font-size: 10px; }
QLabel#MarketTitle { color: #F1F3F5; font-size: 17px; font-weight: 700; }
QLabel#MarketCardTitle { color: #E7E9EC; font-size: 13px; font-weight: 600; }
QLabel#MarketSub { color: #7B818A; font-size: 11px; }
QLabel#MarketUpdated { color: #6C727B; font-size: 11px; }
QLabel#MarketHint { color: #6C727B; font-size: 10px; }
QLabel#MarketStatus { color: #878D96; font-size: 12px; padding: 8px 2px; }
QLabel#MarketStatus[state="error"] { color: #FF9C9C; }
QLabel#TableHead { color: #6C727B; font-size: 10px; font-weight: 600; }
QLabel#TableCell { color: #A6ABB3; font-size: 11px; }
QLabel#TableCellStrong { color: #E7E9EC; font-size: 11px; font-weight: 600; }
QLabel#TableCell[state="up"] { color: #67E396; }
QLabel#TableCell[state="down"] { color: #FF8D8D; }

/* ------------------------------------------------------------ market trade */
QFrame#TradeCard {
    background-color: rgba(255, 255, 255, 5);
    border: 1px solid rgba(255, 255, 255, 18);
    border-radius: 12px;
}
QPushButton#TradeSide {
    background-color: transparent;
    border: 1px solid rgba(255, 255, 255, 26);
    border-radius: 8px;
    padding: 6px 18px;
    color: #B9BEC6;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#TradeSide:hover {
    background-color: rgba(255, 255, 255, 7);
    color: #E9EBEE;
}
QPushButton#TradeSide:checked {
    background-color: @ACCENT_SOFT@;
    border-color: @ACCENT@;
    color: #FFFFFF;
}
QPushButton#TradeQuick {
    background-color: transparent;
    border: 1px solid rgba(255, 255, 255, 20);
    border-radius: 7px;
    padding: 3px 8px;
    color: #9BA1AA;
    font-size: 10px;
}
QPushButton#TradeQuick:hover {
    background-color: rgba(255, 255, 255, 8);
    color: #E9EBEE;
}
QPushButton#TradeQuick:disabled {
    color: #4E545C;
    border-color: rgba(255, 255, 255, 10);
}
QLabel#TradeSum { color: #F1F3F5; font-size: 16px; font-weight: 700; }
QLabel#TradeDelta { color: #9BA1AA; font-size: 13px; font-weight: 700; }
QLabel#TradeDelta[state="good"] { color: #67E396; }
QLabel#TradeDelta[state="bad"] { color: #FF8D8D; }
QLabel#TradeVerdict { color: #7B818A; font-size: 10px; }
QLabel#TradeOwn { color: #6C727B; font-size: 10px; }
QLabel#TradeSaved { color: #67E396; font-size: 11px; }
QLabel#TradeSaved[state="error"] { color: #FF9C9C; }

/* ----------------------------------------------------------------- scroll */
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollArea > QWidget > QWidget {
    background-color: transparent;
}
QWidget#HistoryContent {
    background-color: transparent;
}
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px 0px;
}
QScrollBar::handle:vertical {
    background: #2E333A;
    border-radius: 3px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover {
    background: @ACCENT@;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
QScrollBar:horizontal {
    height: 0px;
}

/* ----------------------------------------------------------- calendar popup */
QFrame#PopupCard {
    background-color: #111317;
    border: 1px solid #2D3239;
    border-radius: 12px;
}
QCalendarWidget QWidget {
    background-color: #111317;
    color: #E7E9EC;
}
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: #111317;
    border-bottom: 1px solid #22262B;
}
QCalendarWidget QToolButton {
    background-color: transparent;
    border: none;
    border-radius: 6px;
    color: #E7E9EC;
    font-size: 12px;
    font-weight: 600;
    padding: 4px 8px;
}
QCalendarWidget QToolButton:hover {
    background-color: rgba(255, 255, 255, 14);
}
QCalendarWidget QToolButton::menu-indicator {
    image: none;
}
QCalendarWidget QMenu {
    background-color: #171A1E;
    border: 1px solid #2D3239;
    color: #E7E9EC;
}
QCalendarWidget QMenu::item:selected {
    background-color: #242B36;
}
QCalendarWidget QSpinBox {
    background-color: #171A1E;
    color: #E7E9EC;
    border: 1px solid #2D3239;
    selection-background-color: @ACCENT@;
}
QCalendarWidget QAbstractItemView:enabled {
    background-color: #111317;
    alternate-background-color: #15181D;
    color: #D7DADF;
    selection-background-color: @ACCENT@;
    selection-color: @ON_ACCENT@;
    outline: 0;
    border: none;
    font-size: 12px;
}
QCalendarWidget QAbstractItemView:disabled {
    color: #565C64;
}
QCalendarWidget QTableView {
    background-color: #111317;
    alternate-background-color: #15181D;
    selection-background-color: @ACCENT@;
    selection-color: @ON_ACCENT@;
    border: none;
}
QCalendarWidget QHeaderView {
    background-color: #111317;
    color: #717780;
    border: none;
}
QCalendarWidget QHeaderView::section {
    background-color: #111317;
    color: #717780;
    border: none;
    padding: 3px 0px;
    font-size: 11px;
}
QLineEdit#TimeSpin {
    min-height: 20px;
    padding: 0px 4px;
    font-size: 13px;
    background-color: #171A1F;
}

/* --------------------------------------------------------------------- misc */
QToolTip {
    background-color: #16191D;
    color: #E9EBEE;
    border: 1px solid #2E333A;
    border-radius: 6px;
    padding: 5px 8px;
}
QLabel#Toast {
    background-color: rgba(25, 28, 33, 246);
    border: 1px solid rgba(255, 255, 255, 24);
    border-radius: 9px;
    padding: 8px 16px;
    color: #F2F4F6;
    font-size: 12px;
}
QMessageBox {
    background-color: #101215;
}
QMessageBox QLabel {
    color: #E7E9EC;
    font-size: 13px;
    min-width: 300px;
}
QMessageBox QPushButton {
    min-width: 84px;
}
QWidget#ImageOverlay {
    background-color: rgba(3, 4, 6, 225);
}
QLabel#OverlayHint {
    color: #8D939B;
    font-size: 12px;
}
QLabel#OverlayTitle {
    color: #F0F2F4;
    font-size: 14px;
    font-weight: 600;
}
QSizeGrip {
    background-color: transparent;
}
"""


DEFAULT_THEME = "dark"
DEFAULT_ACCENT = "#7C9CFF"

ACCENTS: dict[str, tuple[str, str]] = {
    "blue": ("#7C9CFF", "Голубой"),
    "violet": ("#B79CFF", "Лавандовый"),
    "emerald": ("#6FE7B0", "Мятный"),
    "amber": ("#F5C86B", "Песочный"),
    "rose": ("#FF9AAA", "Розовый"),
    "slate": ("#C3CEDD", "Серебристый"),
}

THEMES: dict[str, str] = {
    "dark": "Чёрная",
    "light": "Белая",
}

_ACTIVE_THEME = DEFAULT_THEME


def set_active_theme(theme_name: str) -> str:
    """Remember the theme so widgets can pick readable icon/photo colors."""
    global _ACTIVE_THEME
    _ACTIVE_THEME = theme_name if theme_name in THEMES else DEFAULT_THEME
    return _ACTIVE_THEME


def active_theme() -> str:
    return _ACTIVE_THEME


def icon_tone(role: str = "muted") -> str:
    """Icon color that stays readable in either theme."""
    tones = {
        "muted": ("#8C929A", "#6B7280"),
        "text": ("#D9DDE2", "#33383F"),
        "strong": ("#B8BDC5", "#4B5563"),
        "faint": ("#6C727B", "#8A919B"),
    }
    dark, light = tones.get(role, tones["muted"])
    return light if _ACTIVE_THEME == "light" else dark


LIGHT_QSS = r"""
/* ------------------------------------------------------------- light theme */
QWidget {
    color: #1B1F24;
}
QFrame#Panel {
    background-color: rgba(255, 255, 255, 168);
    border: 1px solid rgba(0, 0, 0, 26);
}
QLabel#FieldLabel { color: #6B7280; }
QLabel#AppTitle { color: #14181D; }
QLabel#HistoryPill {
    background-color: rgba(0, 0, 0, 4);
    border: 1px solid rgba(0, 0, 0, 20);
    color: #22262B;
}
QLabel#CountMuted { color: #7A818B; }
QPushButton#Tab {
    background-color: transparent;
    border: 1px solid transparent;
    color: #7A818B;
}
QPushButton#Tab:hover {
    background-color: rgba(0, 0, 0, 4);
    color: #1B1F24;
}
QPushButton#Tab:checked {
    background-color: rgba(0, 0, 0, 5);
    border-color: rgba(0, 0, 0, 24);
    color: #14181D;
}
QFrame#WeekHeader {
    background-color: rgba(0, 0, 0, 3);
    border: 1px solid rgba(0, 0, 0, 11);
}
QFrame#WeekHeader:hover { background-color: rgba(0, 0, 0, 5); }
QLabel#WeekChevron { color: #6B7280; }
QLabel#WeekTitle { color: #33383F; }
QLabel#WeekMeta { color: #7A818B; }
QLabel#WeekAmount { color: #4B5563; }
QLabel#DragHandle:hover { background-color: rgba(0, 0, 0, 8); }
QFrame#PairHeader {
    background-color: rgba(0, 0, 0, 4);
    border: 1px solid rgba(0, 0, 0, 14);
}
QFrame#PairHeader:hover { background-color: rgba(0, 0, 0, 7); }
QLabel#PairChevron { color: #6B7280; }
QLabel#PairTitle { color: #1B1F24; }
QLabel#PairMeta { color: #7A818B; }
QLabel#PairProfit { color: #4B5563; }
QLabel#PairProfit[state="positive"] { color: #1E8E4E; }
QLabel#PairProfit[state="negative"] { color: #C0392B; }
QLabel#DealTitle { color: #1B1F24; }
QLabel#DealDate { color: #7A818B; }
QLabel#DealComment { color: #4B5563; }
QLabel#EmptyTitle { color: #2A2F36; }
QLabel#EmptyHint { color: #7A818B; }
QLabel#PhotoTitle { color: #262B31; }
QLabel#PhotoHint { color: #7A818B; }
QLabel#PhotoIcon {
    background-color: rgba(0, 0, 0, 4);
    border: 1px solid rgba(0, 0, 0, 10);
}
QLabel#Muted { color: #6B7280; }
QLabel#PopupTitle { color: #14181D; }
QLabel#PopupSection { color: #6B7280; }
QLabel#PopupHint { color: #7A818B; }

QLineEdit, QTextEdit, QComboBox, QSpinBox {
    background-color: rgba(255, 255, 255, 222);
    border: 1px solid #D3D8DF;
    color: #1B1F24;
}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
    background-color: rgba(255, 255, 255, 243);
    border: 1px solid @ACCENT@;
}
QLineEdit[error="true"], QTextEdit[error="true"] {
    border: 1px solid #D9534F;
}
QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid #D3D8DF;
    color: #1B1F24;
    selection-background-color: #EDF1F7;
    selection-color: #111418;
}
QPushButton {
    background-color: #F2F4F7;
    border: 1px solid #D3D8DF;
    color: #22262B;
}
QPushButton:hover { background-color: #E8ECF2; }
QPushButton:pressed { background-color: #DDE3EA; }
QPushButton#Submit {
    background-color: @ACCENT@;
    border: 1px solid @ACCENT@;
    color: @ON_ACCENT@;
}
QPushButton#Submit:hover {
    background-color: @ACCENT_STRONG@;
    border-color: @ACCENT_STRONG@;
}
QPushButton#Submit:pressed { background-color: @ACCENT_DARK@; }
QPushButton#Ghost {
    background-color: transparent;
    border: 1px solid rgba(0, 0, 0, 28);
    color: #4B5563;
}
QPushButton#Ghost:hover {
    background-color: rgba(0, 0, 0, 5);
    color: #14181D;
}
QPushButton#Chip {
    background-color: rgba(255, 255, 255, 150);
    border: 1px solid rgba(0, 0, 0, 22);
    color: #33383F;
}
QPushButton#Chip:hover {
    background-color: rgba(255, 255, 255, 220);
    border-color: rgba(0, 0, 0, 40);
}
QPushButton#PopupGhost {
    background-color: transparent;
    border: 1px solid rgba(0, 0, 0, 24);
    color: #4B5563;
}
QPushButton#PopupGhost:hover { background-color: rgba(0, 0, 0, 5); }
QPushButton#PopupGhost:checked {
    background-color: @ACCENT_SOFT@;
    border-color: @ACCENT@;
    color: #14181D;
}
QPushButton#PopupGhost:disabled {
    background-color: transparent;
    border-color: rgba(0, 0, 0, 14);
    color: #AEB5BF;
}
QPushButton#PopupPrimary {
    background-color: #1B1F24;
    border: 1px solid #1B1F24;
    color: #FFFFFF;
}
QPushButton#PopupPrimary:hover { background-color: #2A3038; }
QPushButton#Danger {
    color: #B33A3A;
    border-color: rgba(179, 58, 58, 90);
}
QPushButton#Danger:hover { background-color: rgba(179, 58, 58, 25); }

QToolButton:hover { background-color: rgba(0, 0, 0, 8); }
QToolButton:pressed { background-color: rgba(0, 0, 0, 4); }
QToolButton#WinBtn:hover { background-color: rgba(0, 0, 0, 10); }
QToolButton#WinClose:hover { background-color: #D94147; }

QFrame#PhotoDrop {
    background-color: rgba(0, 0, 0, 2);
    border: 1px solid #D3D8DF;
}
QFrame#PhotoDrop:hover {
    background-color: rgba(0, 0, 0, 4);
    border-color: #B8C0CA;
}
QFrame#PhotoDrop[filled="true"] {
    background-color: rgba(0, 0, 0, 3);
    border: 1px solid #D3D8DF;
}

QFrame#DealCard[side="buy"] {
    background-color: rgba(255, 226, 228, 165);
    border: 1px solid rgba(199, 62, 69, 55);
}
QFrame#DealCard[side="buy"]:hover {
    background-color: rgba(255, 216, 219, 195);
}
QFrame#DealCard[side="sell"] {
    background-color: rgba(224, 246, 232, 165);
    border: 1px solid rgba(38, 148, 88, 50);
}
QFrame#DealCard[side="sell"]:hover {
    background-color: rgba(211, 241, 223, 195);
}
QLabel#BadgeBuy {
    background-color: rgba(199, 62, 69, 28);
    color: #B33A3A;
}
QLabel#BadgeSell {
    background-color: rgba(38, 148, 88, 25);
    color: #1E8E4E;
}
QLabel#AmountBuy { color: #C0392B; }
QLabel#AmountSell { color: #1E8E4E; }

QFrame#TotalBar {
    background-color: rgba(0, 0, 0, 4);
    border: 1px solid rgba(0, 0, 0, 14);
}
QFrame#TotalBar[state="negative"] {
    background-color: rgba(255, 226, 228, 160);
    border: 1px solid rgba(199, 62, 69, 55);
}
QFrame#TotalBar[state="positive"] {
    background-color: rgba(224, 246, 232, 160);
    border: 1px solid rgba(38, 148, 88, 50);
}
QLabel#TotalCaption { color: #4B5563; }
QLabel#TotalValue { color: #1B1F24; }
QLabel#TotalValue[state="negative"] { color: #C0392B; }
QLabel#TotalValue[state="positive"] { color: #1E8E4E; }

QScrollBar::handle:vertical { background: #C6CDD6; }
QScrollBar::handle:vertical:hover { background: @ACCENT@; }

QFrame#MarketRow {
    background-color: rgba(255, 255, 255, 150);
    border: 1px solid rgba(0, 0, 0, 8);
}
QFrame#MarketRow:hover {
    background-color: #FFFFFF;
    border-color: rgba(0, 0, 0, 22);
}
QLabel#MarketThumb {
    background-color: rgba(0, 0, 0, 4);
    border: 1px solid rgba(0, 0, 0, 10);
    color: #4B5563;
}
QLabel#MarketName { color: #1B1F24; }
QLabel#MarketMeta { color: #7A818B; }
QLabel#MarketPrice { color: #1B1F24; }
QLabel#MarketSold { color: #7A818B; }
QFrame#MarketCard {
    background-color: rgba(255, 255, 255, 150);
    border: 1px solid rgba(0, 0, 0, 12);
}
QFrame#MarketStat {
    background-color: rgba(255, 255, 255, 168);
    border: 1px solid rgba(0, 0, 0, 12);
}
QFrame#MarketStat[highlight="true"] {
    background-color: @ACCENT_SOFT@;
    border-color: @ACCENT@;
}
QLabel#StatLabel { color: #7A818B; }
QLabel#StatValue { color: #14181D; }
QLabel#StatHint { color: #8A919B; }
QLabel#MarketTitle { color: #14181D; }
QLabel#MarketCardTitle { color: #1B1F24; }
QLabel#MarketSub { color: #7A818B; }
QLabel#MarketUpdated { color: #7A818B; }
QLabel#MarketHint { color: #8A919B; }
QLabel#MarketStatus { color: #6B7280; }
QLabel#MarketStatus[state="error"] { color: #B33A3A; }
QLabel#TableHead { color: #7A818B; }
QLabel#TableCell { color: #4B5563; }
QLabel#TableCellStrong { color: #1B1F24; }
QLabel#TableCell[state="up"] { color: #1E8E4E; }
QLabel#TableCell[state="down"] { color: #C0392B; }

/* ------------------------------------------------------------ market trade */
QFrame#TradeCard {
    background-color: rgba(0, 0, 0, 3);
    border: 1px solid rgba(0, 0, 0, 16);
    border-radius: 12px;
}
QPushButton#TradeSide {
    background-color: transparent;
    border: 1px solid rgba(0, 0, 0, 26);
    color: #4B5563;
}
QPushButton#TradeSide:hover {
    background-color: rgba(0, 0, 0, 5);
    color: #14181D;
}
QPushButton#TradeSide:checked {
    background-color: @ACCENT_SOFT@;
    border-color: @ACCENT@;
    color: #14181D;
}
QPushButton#TradeQuick {
    background-color: transparent;
    border: 1px solid rgba(0, 0, 0, 20);
    color: #6B7280;
}
QPushButton#TradeQuick:hover {
    background-color: rgba(0, 0, 0, 5);
    color: #14181D;
}
QPushButton#TradeQuick:disabled {
    color: #B4BAC3;
    border-color: rgba(0, 0, 0, 10);
}
QLabel#TradeSum { color: #14181D; }
QLabel#TradeDelta { color: #6B7280; }
QLabel#TradeDelta[state="good"] { color: #1E8E4E; }
QLabel#TradeDelta[state="bad"] { color: #C0392B; }
QLabel#TradeVerdict { color: #7A818B; }
QLabel#TradeOwn { color: #7A818B; }
QLabel#TradeSaved { color: #1E8E4E; }
QLabel#TradeSaved[state="error"] { color: #B33A3A; }

QFrame#PopupCard {
    background-color: #FFFFFF;
    border: 1px solid #D3D8DF;
}
QCalendarWidget QWidget { background-color: #FFFFFF; color: #1B1F24; }
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E4E8EE;
}
QCalendarWidget QToolButton { color: #1B1F24; }
QCalendarWidget QToolButton:hover { background-color: rgba(0, 0, 0, 7); }
QCalendarWidget QMenu {
    background-color: #FFFFFF;
    border: 1px solid #D3D8DF;
    color: #1B1F24;
}
QCalendarWidget QMenu::item:selected { background-color: #EDF1F7; }
QCalendarWidget QSpinBox {
    background-color: #F3F5F8;
    color: #1B1F24;
    border: 1px solid #D3D8DF;
}
QCalendarWidget QAbstractItemView:enabled {
    background-color: #FFFFFF;
    alternate-background-color: #F6F8FA;
    color: #33383F;
    selection-background-color: @ACCENT@;
    selection-color: @ON_ACCENT@;
}
QCalendarWidget QAbstractItemView:disabled { color: #A9B0BA; }
QCalendarWidget QTableView {
    background-color: #FFFFFF;
    alternate-background-color: #F6F8FA;
    selection-background-color: @ACCENT@;
    selection-color: @ON_ACCENT@;
}
QCalendarWidget QHeaderView { background-color: #FFFFFF; color: #7A818B; }
QCalendarWidget QHeaderView::section {
    background-color: #FFFFFF;
    color: #7A818B;
}
QLineEdit#TimeSpin { background-color: #F3F5F8; }

QToolTip {
    background-color: #FFFFFF;
    color: #1B1F24;
    border: 1px solid #D3D8DF;
}
QLabel#Toast {
    background-color: rgba(255, 255, 255, 245);
    border: 1px solid rgba(0, 0, 0, 22);
    color: #14181D;
}
QMessageBox { background-color: #FFFFFF; }
QMessageBox QLabel { color: #1B1F24; }
"""


def theme_accent(accent: str, theme_name: str = DEFAULT_THEME) -> QColor:
    """Accent used for painting: always readable on the theme background."""
    color = QColor(accent)
    if not color.isValid():
        color = QColor(DEFAULT_ACCENT)
    if theme_name == "light":
        return _ensure_contrast(color, QColor("#F4F6F9"), toward_white=False)
    return _ensure_contrast(color, QColor("#0B0E12"), toward_white=True)


def _channel_luminance(value: int) -> float:
    channel = value / 255
    if channel <= 0.03928:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(color: QColor) -> float:
    return (
        0.2126 * _channel_luminance(color.red())
        + 0.7152 * _channel_luminance(color.green())
        + 0.0722 * _channel_luminance(color.blue())
    )


def contrast_ratio(first: QColor, second: QColor) -> float:
    one = relative_luminance(first)
    two = relative_luminance(second)
    high, low = max(one, two), min(one, two)
    return (high + 0.05) / (low + 0.05)


def contrast_text(background: QColor) -> QColor:
    """White or near-black text, whichever reads better on the background."""
    dark = QColor("#0B0E12")
    light = QColor("#FFFFFF")
    if contrast_ratio(background, dark) >= contrast_ratio(background, light):
        return dark
    return light


def _blend(color: QColor, target: QColor, amount: float) -> QColor:
    return QColor(
        round(color.red() + (target.red() - color.red()) * amount),
        round(color.green() + (target.green() - color.green()) * amount),
        round(color.blue() + (target.blue() - color.blue()) * amount),
    )


def _ensure_contrast(
    color: QColor, background: QColor, toward_white: bool, minimum: float = 4.5
) -> QColor:
    """Подмешать белый или чёрный, пока акцент не станет читаемым."""
    target = QColor("#FFFFFF") if toward_white else QColor("#000000")
    result = QColor(color)
    for _step in range(24):
        if contrast_ratio(result, background) >= minimum:
            break
        result = _blend(result, target, 0.12)
    return result


def palette(theme_name: str = DEFAULT_THEME, accent: str = DEFAULT_ACCENT) -> QPalette:
    highlight = theme_accent(accent, theme_name)
    result = QPalette()
    if theme_name == "light":
        roles = {
            QPalette.ColorRole.Window: "#F4F6F9",
            QPalette.ColorRole.WindowText: "#1B1F24",
            QPalette.ColorRole.Base: "#FFFFFF",
            QPalette.ColorRole.AlternateBase: "#F6F8FA",
            QPalette.ColorRole.Text: "#1B1F24",
            QPalette.ColorRole.Button: "#F2F4F7",
            QPalette.ColorRole.ButtonText: "#1B1F24",
            QPalette.ColorRole.PlaceholderText: "#98A0AA",
            QPalette.ColorRole.ToolTipBase: "#FFFFFF",
            QPalette.ColorRole.ToolTipText: "#1B1F24",
        }
    else:
        roles = {
            QPalette.ColorRole.Window: "#050608",
            QPalette.ColorRole.WindowText: "#E7E9EC",
            QPalette.ColorRole.Base: "#0E1013",
            QPalette.ColorRole.AlternateBase: "#14171B",
            QPalette.ColorRole.Text: "#E7E9EC",
            QPalette.ColorRole.Button: "#1A1D22",
            QPalette.ColorRole.ButtonText: "#E7E9EC",
            QPalette.ColorRole.PlaceholderText: "#5C626B",
            QPalette.ColorRole.ToolTipBase: "#16191D",
            QPalette.ColorRole.ToolTipText: "#E9EBEE",
        }
    for role, color in roles.items():
        result.setColor(role, QColor(color))
    result.setColor(QPalette.ColorRole.Highlight, highlight)
    result.setColor(
        QPalette.ColorRole.HighlightedText, contrast_text(highlight)
    )
    result.setColor(QPalette.ColorRole.Link, highlight)
    return result


def stylesheet(
    chevron_path: str,
    accent: str = DEFAULT_ACCENT,
    theme_name: str = DEFAULT_THEME,
) -> str:
    accent_color = theme_accent(accent, theme_name)
    red, green, blue, _alpha = accent_color.getRgb()
    qss = BASE_QSS if theme_name == "dark" else BASE_QSS + LIGHT_QSS
    replacements = (
        ("@CHEVRON@", chevron_path.replace("\\", "/")),
        ("@ACCENT_SOFT_STRONG@", f"rgba({red}, {green}, {blue}, 60)"),
        ("@ACCENT_SOFT@", f"rgba({red}, {green}, {blue}, 32)"),
        ("@ACCENT_STRONG@", accent_color.darker(112).name()),
        ("@ACCENT_DARK@", accent_color.darker(125).name()),
        ("@ON_ACCENT@", contrast_text(accent_color).name()),
        ("@ACCENT@", accent_color.name()),
    )
    for token, value in replacements:
        qss = qss.replace(token, value)
    return qss
