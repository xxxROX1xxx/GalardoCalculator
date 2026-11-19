from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from PySide6.QtCore import (
    QDate,
    QDateTime,
    QEvent,
    QPoint,
    QPointF,
    QRectF,
    QSize,
    QTimer,
    Qt,
)
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QIcon,
    QImage,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import design, icons, theme, ui_kit
from .db import CATEGORIES, Database, Deal
from .market import KIND_CATEGORY, MarketPanel
from .widgets import (
    AmountLineEdit,
    ClickableLineEdit,
    DateTimePopup,
    DealCard,
    ImageOverlay,
    PairSection,
    PhotoDrop,
    ResizeGrip,
    SettingsPopup,
    TitleBar,
    Toast,
    WeekSection,
    clear_crossfade,
    crossfade_stack,
    deals_word,
    format_money,
    install_press_feedback,
    parse_amount,
    repolish,
)


def amount_to_text(value: float) -> str:
    if abs(value - round(value)) < 0.005:
        return str(int(round(value)))
    return f"{value:.2f}".replace(".", ",")


@dataclass
class HistoryEntry:
    """Строка истории: одиночная сделка или пара «покупка + продажи»."""

    deal: Deal
    children: list[Deal]
    week: int = 0

    @property
    def members(self) -> list[Deal]:
        return [self.deal, *self.children]

    @property
    def ids(self) -> list[int]:
        return [member.id for member in self.members]

    @property
    def total(self) -> float:
        return sum(member.signed_amount for member in self.members)


class MainWindow(QWidget):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self.currency = "$"
        saved_accent = QColor(
            self.db.get_setting("accent", theme.DEFAULT_ACCENT)
        )
        self.accent = (
            saved_accent.name()
            if saved_accent.isValid()
            else theme.DEFAULT_ACCENT
        )
        self.theme_name = self.db.get_setting("theme", theme.DEFAULT_THEME)
        if self.theme_name not in theme.THEMES:
            self.theme_name = theme.DEFAULT_THEME
        self.liquid_glass = self.db.get_setting("liquid_glass", "0") == "1"
        self._editing_id: int | None = None
        self._quick_filled = False
        self._active_tab = "all"
        self._week_expanded: dict[tuple[str, int], bool] = {}
        self._pair_expanded: dict[tuple[str, int], bool] = {}
        self._week_entries: dict[int, list[HistoryEntry]] = {}
        self._pending_parent_id: int | None = None
        self._pending_product = ""
        self._deal_dt = QDateTime.currentDateTime()

        self.setWindowTitle("Galardo")
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(1040, 740)
        self.resize(1180, 760)
        self._center_on_screen()

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(140)
        self._search_timer.timeout.connect(self.refresh_history)

        self.apply_appearance()
        self._build_ui()

        self._date_time_popup = DateTimePopup(self)
        self._date_time_popup.accepted.connect(self._on_deal_dt_selected)
        self._date_time_popup.refresh_shadow(self.theme_name, self.accent)
        self._settings_popup = SettingsPopup(self)
        self._settings_popup.accentChanged.connect(self._on_accent_changed)
        self._settings_popup.themeChanged.connect(self._on_theme_changed)
        self._settings_popup.liquidGlassChanged.connect(self._set_liquid_glass)
        self._settings_popup.refresh_shadow(self.theme_name, self.accent)

        self._overlay = ImageOverlay(self)
        self._toast = Toast(self)
        self.photo.photoAdded.connect(
            lambda: self._toast.show_message("Фотография добавлена")
        )
        self.photo.photoReplaced.connect(
            lambda: self._toast.show_message("Фотография обновлена")
        )

        self._date_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self._date_shortcut.activated.connect(self._on_submit)
        self._date_shortcut2 = QShortcut(QKeySequence("Ctrl+Enter"), self)
        self._date_shortcut2.activated.connect(self._on_submit)

        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
            install_press_feedback(app)
        self.refresh_history()

        imported = getattr(self.db, "legacy_imported", 0)
        if imported:
            QTimer.singleShot(
                900,
                lambda count=imported: self._toast.show_message(
                    f"История старой версии перенесена: {count} "
                    f"{deals_word(count)}"
                ),
            )
        self.product_edit.setFocus()

    def _submit_tint(self) -> str:
        """Цвет значка на акцентной кнопке — контрастный к её фону."""
        accent = theme.theme_accent(self.accent, self.theme_name)
        return theme.contrast_text(accent).name()

    def apply_appearance(self) -> None:
        if hasattr(self, "view_stack"):
            clear_crossfade(self.view_stack)
        theme.set_active_theme(self.theme_name, liquid_glass=self.liquid_glass)
        if self.liquid_glass:
            self._glass_washes = theme.glass_washes(self.accent, self.theme_name)
        app = QApplication.instance()
        if app is not None:
            assets = icons.ensure_ui_assets()
            app.setPalette(
                theme.palette(
                    self.theme_name, self.accent, liquid_glass=self.liquid_glass
                )
            )
            app.setStyleSheet(
                theme.stylesheet(
                    assets["chevron"],
                    self.accent,
                    self.theme_name,
                    liquid_glass=self.liquid_glass,
                )
            )
        self._refresh_icons()
        if hasattr(self, "_panel_surfaces"):
            self._update_panel_shadows()
        for popup_name in ("_settings_popup", "_date_time_popup"):
            popup = getattr(self, popup_name, None)
            if popup is not None:
                popup.refresh_shadow(self.theme_name, self.accent)
        self.update()

    def _refresh_icons(self) -> None:
        """Re-tint icons after the theme changed."""
        if not hasattr(self, "title_bar"):
            return
        tone = theme.icon_tone("muted")
        self.title_bar.refresh_icons()
        self.photo.refresh_icons()
        if hasattr(self, "_refresh_action"):
            self._refresh_action.setIcon(icons.icon("refresh", tone))
        if hasattr(self, "_search_action"):
            self._search_action.setIcon(icons.icon("search", tone))
            self._clear_search_action.setIcon(icons.icon("close", tone))
        if hasattr(self, "submit_button"):
            if self._editing_id is not None:
                self.submit_button.setIcon(icons.icon("check", self._submit_tint()))
            else:
                self.submit_button.setIcon(QIcon())
        if hasattr(self, "market"):
            self.market.refresh_theme(self.accent)
        for index in range(self.history_layout.count()):
            item = self.history_layout.itemAt(index)
            widget = item.widget() if item is not None else None
            if isinstance(widget, DealCard):
                widget.refresh_icons()
            elif isinstance(widget, WeekSection):
                widget.refresh_icons()
        if getattr(self, "_empty_icon", None) is not None:
            pixmap = icons.icon_pixmap(
                "search" if self._empty_searching else "receipt",
                theme.icon_tone("faint"),
                96,
            ).scaled(
                88,
                88,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            pixmap.setDevicePixelRatio(2.0)
            self._empty_icon.setPixmap(pixmap)

    # ------------------------------------------------------------------- building
    def _center_on_screen(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen:
            available = screen.availableGeometry()
            self.move(
                available.center().x() - self.width() // 2,
                available.center().y() - self.height() // 2,
            )

    def _build_ui(self) -> None:
        self._panel_surfaces: list[QFrame] = []
        self._shadow_color = theme.shadow_color(
            self.theme_name, self.accent, strong=True
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.title_bar = TitleBar(self)
        self.title_bar.minimizeRequested.connect(self.showMinimized)
        self.title_bar.maximizeRequested.connect(self._toggle_maximize)
        self.title_bar.closeRequested.connect(self.close)
        self.title_bar.settingsRequested.connect(self._open_settings)
        root.addWidget(self.title_bar)

        content = QHBoxLayout()
        content.setContentsMargins(24, 14, 24, 24)
        content.setSpacing(18)

        form_panel = self.form_panel = self._build_form_panel()
        history_panel = self.history_panel = self._build_history_panel()
        self._register_panel_shadow(form_panel)
        self._register_panel_shadow(history_panel)

        # 43 / 57 keeps both columns readable at 1200 px and wider.
        content.addWidget(form_panel, 43)
        content.addWidget(history_panel, 57)
        root.addLayout(content, 1)

        self._grip = ResizeGrip(self)
        self._grip.raise_()

    def _register_panel_shadow(self, panel: QFrame) -> None:
        """Elevation is painted by the window itself.

        A QGraphicsDropShadowEffect on a panel is repainted from an offscreen
        buffer, and any child update (checked tab, hover, crossfade) can tear
        that buffer: the tab row lost a button and a strip of the title bar
        leaked into the list. Painting the shadow in ``paintEvent`` keeps the
        elevation while every child repaints straight to the backing store.
        """
        self._panel_surfaces.append(panel)
        panel.installEventFilter(self)
        self._update_panel_shadows()

    def _update_panel_shadows(self) -> None:
        self._shadow_color = theme.shadow_color(
            self.theme_name, self.accent, strong=True
        )
        self.update()

    def _paint_panel_shadow(self, painter: QPainter, panel: QFrame) -> None:
        if not panel.isVisible():
            return
        rect = QRectF(panel.mapTo(self, QPoint(0, 0)), panel.size())
        rect.translate(0.0, 5.0)
        base = QColor(self._shadow_color)
        if self.liquid_glass:
            base.setAlphaF(base.alphaF() * 0.58)
        radius = float(design.RADIUS["panel"])
        painter.save()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # Concentric 2 px rings instead of filled shapes: filled layers stack
        # their alpha and turn the shadow into a solid band in the light theme.
        for step in range(1, 15):
            falloff = (1.0 - step / 15.0) ** 2.0
            color = QColor(base)
            color.setAlphaF(max(0.0, min(1.0, base.alphaF() * falloff)))
            painter.setPen(QPen(color, 2.2))
            shape = rect.adjusted(
                -float(step),
                -float(step) * 0.55,
                float(step),
                float(step) * 1.05,
            )
            path = QPainterPath()
            path.addRoundedRect(
                shape, radius + step * 0.45, radius + step * 0.45
            )
            painter.drawPath(path)
        painter.restore()

    def _build_form_panel(self) -> QFrame:
        panel = ui_kit.Panel()
        panel.setMinimumWidth(420)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(0)

        # heading --------------------------------------------------------------
        heading = QWidget()
        heading_box = QVBoxLayout(heading)
        heading_box.setContentsMargins(0, 0, 0, 0)
        heading_box.setSpacing(3)
        title = QLabel("Новая сделка")
        title.setObjectName("PanelTitle")
        heading_box.addWidget(title)
        subtitle = QLabel("Заполните поля — сделка сразу попадёт в историю")
        subtitle.setObjectName("PanelSubtitle")
        heading_box.addWidget(subtitle)
        layout.addWidget(heading)
        layout.addSpacing(14)

        # scrollable fields ----------------------------------------------------
        self.form_scroll = QScrollArea()
        self.form_scroll.setWidgetResizable(True)
        self.form_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.form_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.form_scroll.viewport().setAutoFillBackground(False)

        self.form_content = QWidget()
        self.form_content.setObjectName("FormContent")
        self.form_content.setAttribute(
            Qt.WidgetAttribute.WA_StyledBackground, True
        )
        form = QVBoxLayout(self.form_content)
        form.setContentsMargins(0, 0, 5, 0)
        form.setSpacing(12)

        # product --------------------------------------------------------------
        self.product_edit = QLineEdit()
        self.product_edit.setFixedHeight(44)
        self.product_edit.setPlaceholderText("Например: Truffade Vivo")
        self.product_edit.setClearButtonEnabled(True)
        self.product_edit.returnPressed.connect(self._on_submit)
        self.product_edit.textChanged.connect(
            lambda: self._clear_field_error(self.product_edit)
        )
        self.product_edit.addAction(
            icons.icon("receipt", theme.icon_tone("muted")),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        form.addWidget(self._group("Название товара", self.product_edit))

        # side + amount --------------------------------------------------------
        self.side_combo = QComboBox()
        self.side_combo.setFixedHeight(44)
        self.side_combo.addItem("Купил", "buy")
        self.side_combo.addItem("Продал", "sell")
        self.side_combo.setCursor(Qt.CursorShape.PointingHandCursor)

        self.amount_edit = AmountLineEdit()
        self.amount_edit.setFixedHeight(44)
        self.amount_edit.setPlaceholderText("0")
        self.amount_edit.returnPressed.connect(self._on_submit)
        self.amount_edit.textChanged.connect(
            lambda: self._clear_field_error(self.amount_edit)
        )
        self.amount_edit.addAction(
            icons.icon("chart", theme.icon_tone("muted")),
            QLineEdit.ActionPosition.LeadingPosition,
        )

        deal_row = QHBoxLayout()
        deal_row.setContentsMargins(0, 0, 0, 0)
        deal_row.setSpacing(12)
        deal_row.addWidget(self._group("Что сделал", self.side_combo), 5)
        deal_row.addWidget(self._group("Сумма сделки", self.amount_edit), 6)
        form.addLayout(deal_row)

        # category + deal date ------------------------------------------------
        self.category_combo = QComboBox()
        self.category_combo.setFixedHeight(44)
        self.category_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        for key, name in CATEGORIES.items():
            self.category_combo.addItem(name, key)
        self.category_combo.setToolTip("Категория сделки")

        self.deal_dt_edit = ClickableLineEdit()
        self.deal_dt_edit.setReadOnly(True)
        self.deal_dt_edit.setFixedHeight(44)
        self.deal_dt_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.deal_dt_edit.setToolTip("Изменить дату и время")
        self.deal_dt_edit.setText(self._deal_dt.toString("dd.MM.yyyy HH:mm"))
        self.deal_dt_edit.addAction(
            icons.icon("calendar", theme.icon_tone("muted")),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        refresh_action = self.deal_dt_edit.addAction(
            icons.icon("refresh", theme.icon_tone("muted")),
            QLineEdit.ActionPosition.TrailingPosition,
        )
        self._refresh_action = refresh_action
        refresh_action.setToolTip("Поставить текущее время")
        refresh_action.triggered.connect(self._set_deal_dt_now)
        self.deal_dt_edit.clicked.connect(self._open_deal_dt_picker)
        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(12)
        meta_row.addWidget(self._group("Категория", self.category_combo), 5)
        meta_row.addWidget(self._group("Дата сделки", self.deal_dt_edit), 6)
        form.addLayout(meta_row)

        # comment --------------------------------------------------------------
        self.comment_edit = QTextEdit()
        self.comment_edit.setFixedHeight(84)
        self.comment_edit.setPlaceholderText("Текст комментария...")
        self.comment_edit.setTabChangesFocus(True)
        form.addWidget(self._group("Комментарий", self.comment_edit))

        # photo ----------------------------------------------------------------
        self.photo = PhotoDrop()
        form.addWidget(self._group("Фотография", self.photo))

        form.addStretch(1)
        self.form_scroll.setWidget(self.form_content)
        layout.addWidget(self.form_scroll, 1)

        # pinned submit --------------------------------------------------------
        layout.addSpacing(12)
        divider = QFrame()
        divider.setObjectName("Divider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)
        layout.addSpacing(12)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(8)
        self.submit_button = QPushButton("+ Внести сделку")
        self.submit_button.setObjectName("Submit")
        self.submit_button.setFixedHeight(46)
        self.submit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.submit_button.setToolTip("Ctrl+Enter — сохранить сделку")
        self.submit_button.setIconSize(QSize(16, 16))
        self.submit_button.clicked.connect(self._on_submit)
        buttons.addWidget(self.submit_button, 1)

        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.setObjectName("Ghost")
        self.cancel_button.setFixedHeight(46)
        self.cancel_button.setFixedWidth(96)
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_button.clicked.connect(self._cancel_edit)
        self.cancel_button.hide()
        buttons.addWidget(self.cancel_button)
        layout.addLayout(buttons)

        return panel

    def _build_history_panel(self) -> QFrame:
        panel = ui_kit.Panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(4)
        self._tab_buttons: dict[str, QPushButton] = {}
        for key, label in (
            ("all", "История"),
            ("transport", "Транспорт"),
            ("clothing", "Одежда"),
            ("items", "Предметы"),
            ("market", "Маркет"),
        ):
            button = QPushButton(label)
            button.setObjectName("Tab")
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda _checked=False, k=key: self._select_tab(k)
            )
            self._tab_buttons[key] = button
            header.addWidget(button, 0, Qt.AlignmentFlag.AlignVCenter)
        self._tab_buttons["all"].setChecked(True)
        header.addStretch(1)
        self.count_label = QLabel("0 сделок")
        self.count_label.setObjectName("CountMuted")
        header.addWidget(self.count_label, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(header)

        self.view_stack = QStackedWidget()
        self.history_page = QWidget()
        page_layout = QVBoxLayout(self.history_page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(12)

        self.search_edit = QLineEdit()
        self.search_edit.setFixedHeight(44)
        self.search_edit.setPlaceholderText("Поиск по сделкам")
        self._search_action = self.search_edit.addAction(
            icons.icon("search", theme.icon_tone("muted")),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        self._clear_search_action = self.search_edit.addAction(
            icons.icon("close", theme.icon_tone("muted")),
            QLineEdit.ActionPosition.TrailingPosition,
        )
        self._clear_search_action.setToolTip("Очистить поиск")
        self._clear_search_action.setVisible(False)
        self._clear_search_action.triggered.connect(self.search_edit.clear)
        self.search_edit.textChanged.connect(self._on_search_text)
        page_layout.addWidget(self.search_edit)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll.viewport().setAutoFillBackground(False)

        self.history_content = QWidget()
        self.history_content.setObjectName("HistoryContent")
        self.history_content.setAttribute(
            Qt.WidgetAttribute.WA_StyledBackground, True
        )
        self.history_layout = QVBoxLayout(self.history_content)
        self.history_layout.setContentsMargins(0, 0, 5, 0)
        self.history_layout.setSpacing(9)
        self.scroll.setWidget(self.history_content)
        page_layout.addWidget(self.scroll, 1)

        self.total_bar = QFrame()
        self.total_bar.setObjectName("TotalBar")
        self.total_bar.setFixedHeight(52)
        total_layout = QHBoxLayout(self.total_bar)
        total_layout.setContentsMargins(14, 0, 14, 0)
        total_layout.setSpacing(8)
        self.total_caption = QLabel("Итого:")
        self.total_caption.setObjectName("TotalCaption")
        total_layout.addWidget(self.total_caption)
        total_layout.addStretch(1)
        self.total_value = QLabel(f"{self.currency} 0")
        self.total_value.setObjectName("TotalValue")
        self.total_value.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        total_layout.addWidget(self.total_value)
        page_layout.addWidget(self.total_bar)

        self.view_stack.addWidget(self.history_page)

        self.market = MarketPanel()
        self.market.imageRequested.connect(self._show_market_image)
        self.market.tradeRequested.connect(self._on_market_trade)
        self.market.tradePhotoReady.connect(self._on_market_trade_photo)
        self.market.set_stats_provider(self._market_stats)
        self.view_stack.addWidget(self.market)

        layout.addWidget(self.view_stack, 1)

        return panel

    def _group(self, label_text: str, widget: QWidget) -> QWidget:
        container = QWidget()
        container.setObjectName("FieldGroup")
        box = QVBoxLayout(container)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(5)
        label = QLabel(label_text)
        label.setObjectName("FieldLabel")
        box.addWidget(label)
        box.addWidget(widget)
        return container

    # ------------------------------------------------------------------- history
    def _select_tab(self, key: str) -> None:
        if key not in self._tab_buttons:
            return
        self._active_tab = key
        self._tab_buttons[key].setChecked(True)
        if key == "market":
            self.count_label.hide()
            crossfade_stack(
                self.view_stack, self.market, 170, update=self.market.ensure_loaded
            )
            self.market.search.setFocus()
            return
        self.count_label.show()
        crossfade_stack(
            self.view_stack, self.history_page, 170, update=self.refresh_history
        )

    def _remember_week(self, week: int, expanded: bool) -> None:
        self._week_expanded[(self._active_tab, week)] = expanded

    def _remember_pair(self, deal_id: int, expanded: bool) -> None:
        self._pair_expanded[(self._active_tab, deal_id)] = expanded

    def _refresh_stats(self) -> None:
        """Top bar metrics always reflect the whole journal, not the filter."""
        deals = self.db.all_deals()
        total = sum(deal.signed_amount for deal in deals)
        closed, active = self.db.position_counts()
        self.title_bar.set_stats(total, closed, active, self.currency)

    def refresh_history(self) -> None:
        self._refresh_stats()
        if getattr(self, "_active_tab", "all") == "market":
            return
        query = self.search_edit.text().strip()
        category = None if self._active_tab == "all" else self._active_tab
        deals = self.db.all_deals(query, category)

        self._clear_history()
        self._week_entries = {}

        if not deals:
            self.history_layout.addStretch(1)
            self.history_layout.addWidget(self._make_empty_state(bool(query)))
            self.history_layout.addStretch(2)
        else:
            anchor = self._history_anchor(deals)
            entries = self._history_entries(deals, anchor)
            weeks: dict[int, list[HistoryEntry]] = {}
            for entry in entries:
                weeks.setdefault(entry.week, []).append(entry)
            self._week_entries = weeks
            newest = max(weeks)
            for week in sorted(weeks, reverse=True):
                group = weeks[week]
                start = anchor.addDays(week * 7)
                end = start.addDays(6)
                expanded = self._week_expanded.get(
                    (self._active_tab, week), week == newest
                )
                section = WeekSection(
                    week + 1,
                    start.date(),
                    end.date(),
                    sum(len(entry.members) for entry in group),
                    sum(entry.total for entry in group),
                    self.currency,
                    expanded,
                    week,
                )
                for entry in group:
                    if entry.children:
                        widget = self._make_pair_section(entry, week)
                    else:
                        card = self._make_deal_card(entry.deal)
                        card.enable_drag(entry.ids, week)
                        card.entry_ids = entry.ids
                        widget = card
                    section.add_card(widget)
                section.toggled.connect(
                    lambda state, index=week: self._remember_week(index, state)
                )
                section.dealDropped.connect(
                    lambda ids, index, number=week: self._on_deal_dropped(
                        number, ids, index
                    )
                )
                self.history_layout.addWidget(section)
            self.history_layout.addStretch(1)

        total = sum(deal.signed_amount for deal in deals)
        self._update_total(total, bool(query))
        self.count_label.setText(f"{len(deals)} {deals_word(len(deals))}")
        QTimer.singleShot(0, self._scroll_to_top)

    def _make_deal_card(self, deal: Deal) -> DealCard:
        card = DealCard(deal, self.currency)
        card.editRequested.connect(self._load_deal_for_edit)
        card.deleteRequested.connect(self._confirm_delete)
        card.copyRequested.connect(self._copy_deal)
        card.quickRequested.connect(self._quick_add)
        card.photoRequested.connect(self._show_photo)
        return card

    def _make_pair_section(self, entry: HistoryEntry, week: int) -> PairSection:
        expanded = self._pair_expanded.get(
            (self._active_tab, entry.deal.id), True
        )
        pair = PairSection(entry.deal, entry.children, self.currency, expanded)
        pair.entry_ids = entry.ids
        pair.editRequested.connect(self._load_deal_for_edit)
        pair.deleteRequested.connect(self._confirm_delete)
        pair.copyRequested.connect(self._copy_pair)
        # сверху продажа, под ней покупка
        for member in [*entry.children, entry.deal]:
            pair.add_card(self._make_deal_card(member))
        pair.enable_drag(entry.ids, week)
        pair.toggled.connect(
            lambda state, deal_id=entry.deal.id: self._remember_pair(
                deal_id, state
            )
        )
        return pair

    def _history_anchor(self, deals: list[Deal]) -> QDateTime:
        anchor = QDateTime.fromString(
            self.db.first_dealt_at() or "", Qt.DateFormat.ISODate
        )
        if not anchor.isValid() and deals:
            anchor = QDateTime.fromString(
                deals[-1].dealt_at, Qt.DateFormat.ISODate
            )
        if not anchor.isValid():
            anchor = QDateTime.currentDateTime()
        return anchor

    def _week_index(self, anchor: QDateTime, deal: Deal) -> int:
        moment = QDateTime.fromString(deal.dealt_at, Qt.DateFormat.ISODate)
        if not moment.isValid():
            moment = anchor
        return int(anchor.secsTo(moment) // (7 * 86400))

    def _history_entries(
        self, deals: list[Deal], anchor: QDateTime
    ) -> list[HistoryEntry]:
        """Разложить сделки на строки: пары только по явной связи parent_id."""
        by_id = {deal.id: deal for deal in deals}
        children: dict[int, list[Deal]] = {}
        for deal in deals:
            parent_id = deal.parent_id
            if parent_id is None or parent_id == deal.id or parent_id not in by_id:
                continue
            children.setdefault(parent_id, []).append(deal)

        entries: list[HistoryEntry] = []
        used: set[int] = set()
        for deal in deals:
            if deal.id in used:
                continue
            parent_id = deal.parent_id
            if parent_id in by_id and parent_id != deal.id:
                # продажа показывается внутри своей покупки
                continue
            group = self._descendants(deal, children, used)
            used.add(deal.id)
            entry = HistoryEntry(deal=deal, children=group)
            entry.week = max(
                self._week_index(anchor, member) for member in entry.members
            )
            entries.append(entry)
        return entries

    def _descendants(
        self, deal: Deal, children: dict[int, list[Deal]], used: set[int]
    ) -> list[Deal]:
        result: list[Deal] = []
        for child in children.get(deal.id, []):
            if child.id in used:
                continue
            used.add(child.id)
            result.append(child)
            result.extend(self._descendants(child, children, used))
        return result

    def _on_deal_dropped(self, week: int, ids: list[int], index: int) -> None:
        """Перетащили строку внутри недели: запоминаем новый порядок."""
        visible = self._week_entries.get(week)
        if not visible:
            return
        dragged = next((entry for entry in visible if entry.ids == ids), None)
        if dragged is None:
            return
        moved = [entry for entry in visible if entry is not dragged]
        index = max(0, min(index, len(moved)))
        new_order = list(moved)
        new_order.insert(index, dragged)
        if new_order == visible:
            return

        # новое место определяем по видимым строкам, а перенумеровываем
        # всю неделю, чтобы не сбить порядок скрытых фильтром сделок
        before = index < len(moved)
        anchor_ids = moved[index].ids if before else (moved[-1].ids if moved else None)

        entries = self._full_week_entries(week)
        target = next((entry for entry in entries if entry.ids == ids), None)
        if target is None:
            return
        entries = [entry for entry in entries if entry.ids != ids]
        position = len(entries)
        for pos, entry in enumerate(entries):
            if entry.ids == anchor_ids:
                position = pos if before else pos + 1
                break
        entries.insert(position, target)

        keys: dict[int, float] = {}
        for pos, entry in enumerate(entries):
            base = float(pos) * 10.0
            keys[entry.deal.id] = base
            for offset, child in enumerate(entry.children, start=1):
                keys[child.id] = base + 0.001 * offset
        self.db.set_sort_keys(keys)

        scroll = self.scroll.verticalScrollBar().value()
        self.refresh_history()
        QTimer.singleShot(
            0, lambda: self.scroll.verticalScrollBar().setValue(scroll)
        )

    def _full_week_entries(self, week: int) -> list[HistoryEntry]:
        deals = self.db.all_deals()
        anchor = self._history_anchor(deals)
        return [
            entry
            for entry in self._history_entries(deals, anchor)
            if entry.week == week
        ]

    def _clear_history(self) -> None:
        while self.history_layout.count():
            item = self.history_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()
        self._empty_icon = None

    def _make_empty_state(self, searching: bool) -> QWidget:
        widget = QWidget()
        box = QVBoxLayout(widget)
        box.setContentsMargins(10, 46, 10, 46)
        box.setSpacing(8)

        icon = QLabel()
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = icons.icon_pixmap(
            "search" if searching else "receipt", theme.icon_tone("faint"), 96
        ).scaled(
            88,
            88,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        pixmap.setDevicePixelRatio(2.0)
        icon.setPixmap(pixmap)
        self._empty_icon = icon
        self._empty_searching = searching
        box.addWidget(icon)

        if searching:
            title_text = "Ничего не найдено"
            hint_text = "Попробуйте изменить запрос"
        elif self._active_tab != "all":
            title_text = "В этой категории пока нет сделок"
            hint_text = "Добавьте сделку и выберите эту категорию"
        else:
            title_text = "Пока нет сделок"
            hint_text = "Добавьте первую сделку в форме слева"

        title = QLabel(title_text)
        title.setObjectName("EmptyTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.addWidget(title)

        hint = QLabel(hint_text)
        hint.setObjectName("EmptyHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        box.addWidget(hint)
        return widget

    def _update_total(self, total: float, searching: bool) -> None:
        state = "negative" if total < -0.0001 else "positive" if total > 0.0001 else ""
        self.total_bar.setProperty("state", state)
        self.total_value.setProperty("state", state)
        repolish(self.total_bar)
        repolish(self.total_value)
        self.total_value.setText(format_money(total, self.currency))
        self.total_caption.setText("Итого по поиску:" if searching else "Итого:")

    def _scroll_to_top(self) -> None:
        self.scroll.verticalScrollBar().setValue(0)

    def _on_search_text(self, text: str) -> None:
        self._clear_search_action.setVisible(bool(text))
        self._search_timer.start()

    # --------------------------------------------------------------------- form
    def _set_error(self, widget: QWidget, active: bool) -> None:
        widget.setProperty("error", bool(active))
        repolish(widget)

    def _clear_errors(self) -> None:
        self._set_error(self.product_edit, False)
        self._set_error(self.amount_edit, False)

    def _clear_field_error(self, widget: QWidget) -> None:
        if widget.property("error"):
            self._set_error(widget, False)

    def _on_submit(self) -> None:
        product = self.product_edit.text().strip()
        amount = parse_amount(self.amount_edit.text())

        self._clear_errors()
        if not product:
            self._set_error(self.product_edit, True)
            self._toast.show_message("Укажите название товара")
            self.product_edit.setFocus()
            return
        if amount is None:
            self._set_error(self.amount_edit, True)
            self._toast.show_message("Укажите сумму сделки")
            self.amount_edit.setFocus()
            return

        side = str(self.side_combo.currentData())
        dealt_at = self._deal_dt.toString(Qt.DateFormat.ISODate)
        comment = self.comment_edit.toPlainText().strip()
        photo = self.photo.photo_bytes()
        category = str(self.category_combo.currentData() or "transport")

        try:
            if self._editing_id is None:
                parent_id = None
                if side == "sell" and self._pending_parent_id is not None:
                    matches = (
                        not self._pending_product
                        or product.casefold() == self._pending_product.casefold()
                    )
                    if matches and self.db.get_deal(self._pending_parent_id):
                        parent_id = self._pending_parent_id
                self.db.add_deal(
                    product=product,
                    side=side,
                    amount=amount,
                    dealt_at=dealt_at,
                    comment=comment,
                    photo=photo,
                    created_at=QDateTime.currentDateTime().toString(
                        Qt.DateFormat.ISODate
                    ),
                    category=category,
                    parent_id=parent_id,
                )
                message = (
                    "Продажа добавлена к покупке"
                    if parent_id is not None
                    else "Сделка добавлена"
                )
            else:
                self.db.update_deal(
                    self._editing_id,
                    product=product,
                    side=side,
                    amount=amount,
                    dealt_at=dealt_at,
                    comment=comment,
                    photo=photo,
                    category=category,
                )
                message = "Сделка обновлена"
        except Exception:
            self._toast.show_message("Не удалось сохранить сделку")
            return

        self._reset_form()
        self.refresh_history()
        self._toast.show_message(message)

    def _reset_form(self) -> None:
        self._editing_id = None
        self._quick_filled = False
        self._pending_parent_id = None
        self._pending_product = ""
        self.product_edit.clear()
        self.amount_edit.clear()
        self.comment_edit.clear()
        self.photo.clear()
        self._clear_errors()
        self.category_combo.setCurrentIndex(0)
        self._deal_dt = QDateTime.currentDateTime()
        self.deal_dt_edit.setText(self._deal_dt.toString("dd.MM.yyyy HH:mm"))
        self.submit_button.setText("+ Внести сделку")
        self.submit_button.setIcon(QIcon())
        self.cancel_button.hide()
        self.product_edit.setFocus()

    def _load_deal_for_edit(self, deal_id: int) -> None:
        deal = self.db.get_deal(deal_id)
        if deal is None:
            return
        self._editing_id = deal.id
        self._quick_filled = False
        self._pending_parent_id = None
        self._pending_product = ""
        self.product_edit.setText(deal.product)
        self.amount_edit.setText(amount_to_text(deal.amount))
        side_index = 0 if deal.side == "buy" else 1
        self.side_combo.setCurrentIndex(side_index)
        category_index = self.category_combo.findData(deal.category)
        self.category_combo.setCurrentIndex(category_index if category_index >= 0 else 0)
        self.comment_edit.setPlainText(deal.comment)
        self.photo.set_bytes(deal.photo)

        dealt = QDateTime.fromString(deal.dealt_at, Qt.DateFormat.ISODate)
        self._deal_dt = dealt if dealt.isValid() else QDateTime.currentDateTime()
        self.deal_dt_edit.setText(self._deal_dt.toString("dd.MM.yyyy HH:mm"))

        self.submit_button.setText("Сохранить изменения")
        self.submit_button.setIcon(icons.icon("check", self._submit_tint()))
        self.cancel_button.show()
        self._clear_errors()
        self.product_edit.setFocus()
        self._toast.show_message("Редактирование сделки")

    def _cancel_edit(self) -> None:
        if self._editing_id is None and not self._quick_filled:
            return
        self._reset_form()
        self._toast.show_message("Редактирование отменено")

    def _confirm_delete(self, deal_id: int) -> None:
        deal = self.db.get_deal(deal_id)
        if deal is None:
            return

        box = QMessageBox(self)
        box.setWindowTitle("Удаление сделки")
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setText("Удалить эту сделку?")
        box.setInformativeText(
            f"«{deal.product}» будет удалена из истории без возможности восстановления."
        )
        box.setIcon(QMessageBox.Icon.NoIcon)
        delete_button = box.addButton("Удалить", QMessageBox.ButtonRole.DestructiveRole)
        delete_button.setObjectName("Danger")
        repolish(delete_button)
        cancel_button = box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(cancel_button)
        box.exec()

        if box.clickedButton() is delete_button:
            try:
                self.db.delete_deal(deal_id)
            except Exception:
                self._toast.show_message("Не удалось удалить сделку")
                return
            if self._editing_id == deal_id:
                self._reset_form()
            self.refresh_history()
            self._toast.show_message("Сделка удалена")

    def _quick_add(self, deal_id: int, side: str) -> None:
        deal = self.db.get_deal(deal_id)
        if deal is None:
            return
        self._editing_id = None
        self._quick_filled = True
        self._pending_parent_id = None
        self._pending_product = ""
        self.product_edit.setText(deal.product)
        self.amount_edit.setText(amount_to_text(deal.amount))
        self.side_combo.setCurrentIndex(0 if side == "buy" else 1)
        category_index = self.category_combo.findData(deal.category)
        self.category_combo.setCurrentIndex(category_index if category_index >= 0 else 0)
        self.comment_edit.setPlainText(deal.comment)
        self.photo.set_bytes(deal.photo)
        self._deal_dt = QDateTime.currentDateTime()
        self.deal_dt_edit.setText(self._deal_dt.toString("dd.MM.yyyy HH:mm"))
        self._clear_errors()
        self.submit_button.setText("+ Внести сделку")
        self.submit_button.setIcon(QIcon())
        self.cancel_button.show()
        self.amount_edit.setFocus()
        self.amount_edit.selectAll()

        linked = False
        if side == "sell" and deal.side == "buy":
            # пара создаётся только по явной связи и только одна продажа
            if self.db.linked_sales(deal.id) == 0:
                self._pending_parent_id = deal.id
                self._pending_product = deal.product
                linked = True
        self._toast.show_message(
            "Продажа встанет рядом с покупкой — проверьте сумму"
            if linked
            else "Данные подставлены — проверьте сумму и нажмите «Внести»"
        )

    def _show_photo(self, deal_id: int) -> None:
        deal = self.db.get_deal(deal_id)
        if deal and deal.photo:
            self._overlay.show_image(deal.photo, deal.product)

    @staticmethod
    def _deal_moment(deal: Deal) -> str:
        moment = QDateTime.fromString(deal.dealt_at, Qt.DateFormat.ISODate)
        return moment.toString("dd.MM.yyyy HH:mm") if moment.isValid() else deal.dealt_at

    def _copy_to_clipboard(self, text: str, message: str) -> None:
        QGuiApplication.clipboard().setText(text)
        self._toast.show_message(message)

    def _copy_deal(self, deal_id: int) -> None:
        deal = self.db.get_deal(deal_id)
        if deal is None:
            return
        lines = [
            f"{'Купил' if deal.side == 'buy' else 'Продал'}: {deal.product}",
            f"Категория: {CATEGORIES.get(deal.category, deal.category)}",
            f"Сумма: {format_money(deal.signed_amount, self.currency)}",
            f"Дата: {self._deal_moment(deal)}",
        ]
        if deal.comment:
            lines.append(f"Комментарий: {deal.comment}")
        self._copy_to_clipboard("\n".join(lines), "Сделка скопирована")

    def _copy_pair(self, deal_id: int) -> None:
        deal = self.db.get_deal(deal_id)
        if deal is None:
            return
        children = [
            item for item in self.db.all_deals() if item.parent_id == deal.id
        ]
        total = deal.signed_amount + sum(item.signed_amount for item in children)
        lines = [
            f"Пара: {deal.product}",
            f"Покупка: {format_money(deal.amount, self.currency, with_sign=False)}",
            f"Продажа: "
            f"{format_money(sum(item.amount for item in children), self.currency, with_sign=False)}",
            f"Итог: {format_money(total, self.currency)}",
            f"Дата: {self._deal_moment(deal)}",
        ]
        self._copy_to_clipboard("\n".join(lines), "Пара скопирована")

    def _show_market_image(self, image: QImage, title: str) -> None:
        self._overlay.show_qimage(image, title)

    def _market_stats(
        self, product: str, kind: str
    ) -> tuple[int, float | None, int, float | None]:
        """Мои сделки по предмету маркета за 30 дней (для карточки маркета)."""
        category = KIND_CATEGORY.get(kind, "transport")
        return self.db.market_own_stats(product, category, 30)

    def _on_market_trade(self, payload: dict) -> None:
        """Сделка из карточки маркета: пишем её в общий журнал."""
        try:
            price = float(payload.get("price") or 0.0)
            quantity = max(1, int(payload.get("quantity") or 1))
        except (TypeError, ValueError):
            return
        if price <= 0:
            return
        product = str(payload.get("product") or "").strip()
        if not product:
            return

        amount = price * quantity
        comment = str(payload.get("comment") or "").strip()
        if quantity > 1:
            unit = (
                f"{quantity} шт. × "
                f"{format_money(price, self.currency, with_sign=False)}"
            )
            comment = f"{comment} · {unit}" if comment else unit

        now = QDateTime.currentDateTime()
        deal_id = self.db.add_deal(
            product=product,
            side=str(payload.get("side") or "buy"),
            amount=amount,
            dealt_at=now.toString(Qt.DateFormat.ISODate),
            comment=comment,
            photo=payload.get("photo") or None,
            created_at=now.toString(Qt.DateFormat.ISODate),
            category=str(payload.get("category") or "transport"),
            quantity=quantity,
        )
        self.market.notify_trade_saved(payload, deal_id)
        word = "Покупка" if payload.get("side") == "buy" else "Продажа"
        self._toast.show_message(
            f"{word} внесена в историю: "
            f"{format_money(amount, self.currency, with_sign=False)}"
        )
        self.refresh_history()

    def _on_market_trade_photo(self, deal_id: int, photo: bytes) -> None:
        """Догрузили картинку маркета уже после сохранения сделки."""
        if not photo:
            return
        self.db.set_deal_photo(deal_id, photo)
        self.refresh_history()

    # --------------------------------------------------------------------- dates
    def _open_deal_dt_picker(self) -> None:
        self._date_time_popup.open_for(self.deal_dt_edit, self._deal_dt)

    def _on_deal_dt_selected(self, value: QDateTime) -> None:
        self._deal_dt = value
        self.deal_dt_edit.setText(value.toString("dd.MM.yyyy HH:mm"))

    def _set_deal_dt_now(self) -> None:
        self._deal_dt = QDateTime.currentDateTime()
        self.deal_dt_edit.setText(self._deal_dt.toString("dd.MM.yyyy HH:mm"))

    # ---------------------------------------------------------------- appearance
    def _open_settings(self) -> None:
        self._settings_popup.open_for(
            self.title_bar.settings_button,
            self.accent,
            self.theme_name,
            liquid_glass=self.liquid_glass,
        )

    def _on_accent_changed(self, accent: str) -> None:
        self.accent = accent
        self.db.set_setting("accent", accent)
        self.apply_appearance()

    def _on_theme_changed(self, theme_name: str) -> None:
        if theme_name not in theme.THEMES or theme_name == self.theme_name:
            return
        self.theme_name = theme_name
        self.db.set_setting("theme", theme_name)
        self.apply_appearance()
        self._toast.show_message(
            "Включена белая тема" if theme_name == "light" else "Включена чёрная тема"
        )

    def _set_liquid_glass(self, enabled: bool) -> None:
        if not self._on_liquid_glass_changed(enabled):
            self._settings_popup.set_liquid_glass(self.liquid_glass)

    def _on_liquid_glass_changed(self, enabled: bool) -> bool:
        if enabled == self.liquid_glass:
            return True
        try:
            with self.db._conn:
                self.db.set_setting("liquid_glass", "1" if enabled else "0")
        except sqlite3.Error:
            self._toast.show_message("Не удалось сохранить настройку Liquid Glass")
            return False
        self.liquid_glass = enabled
        self.apply_appearance()
        return True

    # -------------------------------------------------------------------- events
    def _photo_paste_allowed(self) -> bool:
        """Ctrl+V puts an image from the clipboard into the photo field.

        Image wins over text when the clipboard holds both (copying a picture
        from a browser adds the link text next to it).  Text-only clipboards
        keep normal pasting in the product and comment fields.
        """
        mime = QApplication.clipboard().mimeData()
        if mime is None:
            return False
        return mime.hasImage() or mime.hasUrls()

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if (
            event.type() == QEvent.Type.KeyPress
            and self.isActiveWindow()
            and event.matches(QKeySequence.StandardKey.Paste)
            and self._photo_paste_allowed()
            and self.photo.paste_from_clipboard()
        ):
            event.accept()
            return True
        panels = getattr(self, "_panel_surfaces", ())
        if obj in panels and event.type() in (
            QEvent.Type.Resize,
            QEvent.Type.Move,
            QEvent.Type.Show,
            QEvent.Type.Hide,
        ):
            # The elevation lives in the window background, so it has to be
            # repainted whenever a column changes size or position.
            self.update()
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            if self._overlay.isVisible():
                self._overlay.hide()
                return
            if self._editing_id is not None or self._quick_filled:
                self._cancel_edit()
                return
        super().keyPressEvent(event)

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        elif self.isFullScreen():
            self.showNormal()
        else:
            self.showMaximized()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._grip.move(self.width() - 20, self.height() - 20)
        self._grip.raise_()
        self._sync_window_state()
        if hasattr(self, "_overlay") and self._overlay.isVisible():
            self._overlay.setGeometry(self.rect())
        if hasattr(self, "_toast") and self._toast.isVisible():
            self._toast._reposition()

    def _sync_window_state(self) -> None:
        maximized = self.isMaximized() or self.isFullScreen()
        if hasattr(self, "title_bar"):
            self.title_bar.set_maximized(maximized)
        if hasattr(self, "_grip"):
            self._grip.setVisible(not maximized)

    def changeEvent(self, event) -> None:  # noqa: N802
        if event.type() == QEvent.Type.WindowStateChange:
            self._sync_window_state()
            self.update()
        super().changeEvent(event)

    def _paint_glass_backdrop(self, painter: QPainter, rect: QRectF) -> None:
        primary, reflection = self._glass_washes
        span = max(rect.width(), rect.height())
        for x, y, radius, color in (
            (0.12, 0.14, 0.65, primary),
            (0.91, 0.82, 0.67, reflection),
        ):
            center = QPointF(
                rect.left() + x * rect.width(), rect.top() + y * rect.height()
            )
            wash = QRadialGradient(center, radius * span)
            wash.setColorAt(0.0, color)
            outer = QColor(color)
            outer.setAlpha(0)
            wash.setColorAt(1.0, outer)
            painter.fillRect(rect, wash)

        header_bottom = self.title_bar.height()
        glint = QColor(255, 255, 255, 96 if self.theme_name == "light" else 27)
        clear = QColor(glint)
        clear.setAlpha(0)
        header = QLinearGradient(0, rect.top(), 0, header_bottom)
        header.setColorAt(0, glint)
        header.setColorAt(1, clear)
        painter.fillRect(QRectF(0, 0, rect.width(), header_bottom), header)
        painter.setPen(QPen(primary, 1))
        painter.drawLine(
            QPointF(rect.left(), header_bottom), QPointF(rect.right(), header_bottom)
        )

    def paintEvent(self, event) -> None:  # noqa: N802
        """Paint the clipped backdrop and elevation in the window backing store."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = 0.0 if (self.isMaximized() or self.isFullScreen()) else 16.0
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        painter.setClipPath(path)

        theme_tokens = design.tokens(self.theme_name, liquid_glass=self.liquid_glass)
        base = QLinearGradient(0, 0, 0, self.height())
        base.setColorAt(0.0, QColor(theme_tokens.bg_top))
        base.setColorAt(0.55, QColor(theme_tokens.bg))
        base.setColorAt(1.0, QColor(theme_tokens.bg_bottom))
        painter.fillPath(path, base)
        if self.liquid_glass:
            self._paint_glass_backdrop(painter, rect)

        for panel in getattr(self, "_panel_surfaces", ()):
            self._paint_panel_shadow(painter, panel)

        if radius:
            painter.setPen(QPen(QColor(theme_tokens.border), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

    def closeEvent(self, event) -> None:  # noqa: N802
        self.db.close()
        super().closeEvent(event)
