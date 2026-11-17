from __future__ import annotations

"""Вкладка «Маркет»: статистика цен и продаж с m5rp.ru.

Источник — открытые JSON-файлы m5rp.ru (без авторизации):

    /public/data/server_<ID>.json            каталог + агрегаты за 30 дней
    /public/data/history/<ID>/<bucket>.json  дневная история по ключам
    /data/clothes-images.json                картинки одежды

Пока поддержан один сервер — Phoenix (RU15) Majestic RP.
"""

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import (
    QObject,
    QPointF,
    QRectF,
    Qt,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QImage,
    QIntValidator,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import icons, paths, theme
from .clothing_wiki import WIKI_CLOTHES
from .widgets import (
    AmountLineEdit,
    ElidedLabel,
    format_money,
    image_to_jpeg,
    parse_amount,
    repolish,
    safe_tooltip,
)

BASE = "https://m5rp.ru"
SERVER_ID = "RU15"
SERVER_NAME = "Phoenix"
SERVER_LABEL = f"{SERVER_NAME} · {SERVER_ID}"
CURRENCY = "$"
PERIOD_DAYS = 30
PAGE_SIZE = 30
PREFIX = "majestic"

CATALOG_URL = f"{BASE}/public/data/server_{SERVER_ID}.json"
IMAGES_URL = f"{BASE}/data/clothes-images.json"
ITEM_IMAGE_BASE = (
    "https://cdn-world.majestic-files.net/public/master/static/img/inventory/items"
)
VEHICLE_IMAGE_BASE = (
    "https://cdn-world.majestic-files.net/public/master/static/img/vehicles"
)
CATALOG_TTL = 6 * 3600
IMAGES_TTL = 7 * 24 * 3600
HISTORY_TTL = 5 * 60
IMAGE_RETRY_DELAY = 900
IMAGE_FAIL_TTL = 300

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/152.0 Safari/537.36"
)

KIND_LABEL = {"clothes": "Одежда", "items": "Предметы", "vehicles": "Транспорт"}
KIND_ONE = {"clothes": "Одежда", "items": "Предмет", "vehicles": "Транспорт"}
# категория сделки в журнале для раздела маркета
KIND_CATEGORY = {
    "clothes": "clothing",
    "items": "items",
    "vehicles": "transport",
}

# слоты базовой одежды GTA: у неё нет названий в источнике, но по component
# видно, что это за вещь — так позиции отличаются друг от друга
CLOTH_SLOTS = {
    0: "Голова",
    1: "Маска",
    2: "Волосы",
    3: "Перчатки",
    4: "Штаны",
    5: "Сумка",
    6: "Обувь",
    7: "Аксессуар",
    8: "Майка",
    9: "Броня",
    10: "Нашивка",
    11: "Верх",
}
PROP_SLOTS = {
    0: "Головной убор",
    1: "Очки",
    2: "Серьги",
    6: "Часы",
    7: "Браслет",
}


def cloth_slot(component: int, is_prop: bool) -> str:
    if is_prop:
        return PROP_SLOTS.get(component, "Аксессуар")
    return CLOTH_SLOTS.get(component, "Одежда")

MONTHS = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)


# --------------------------------------------------------------------------- data


@dataclass
class MarketEntry:
    key: str
    kind: str
    ident: str
    name: str
    image: str | None
    sold: int
    avg: float
    min: float
    max: float
    total: int
    gender: int = 0
    texture: int = 0
    component: int = 0
    drawable: int = 0
    is_prop: bool = False
    unnamed: bool = False
    group: str = ""
    slot: str = ""
    image_alt: str | None = None

    @property
    def subtitle(self) -> str:
        if self.kind == "clothes":
            parts = [self.slot or ("Аксессуар" if self.is_prop else "Одежда")]
            parts.append("Женская" if self.gender == 1 else "Мужская")
            if self.drawable:
                parts.append(f"модель {self.drawable}")
            parts.append(f"цвет {self.texture}")
            return " · ".join(parts)
        parts = [KIND_ONE[self.kind]]
        if self.unnamed:
            parts.append("нет названия в источнике")
            return " · ".join(parts)
        if self.ident:
            parts.append(f"ID {self.ident}")
        return " · ".join(parts)


@dataclass
class HistoryPoint:
    day: str
    avg: float
    min: float
    max: float
    sold: int


# ------------------------------------------------------------------------ helpers


def bucket_of(key: str) -> int:
    """Имя корзины истории: n = (n * 31 + byte) % 128 (как в коде m5rp)."""
    value = 0
    for byte in key.encode("utf-8"):
        value = (value * 31 + byte) % 128
    return value


def compact(value: float) -> str:
    value = abs(value)
    if value >= 1e9:
        return f"{value / 1e9:.2f} млрд".replace(".", ",")
    if value >= 1e6:
        return f"{value / 1e6:.2f} млн".replace(".", ",")
    if value >= 1e3:
        return f"{value / 1e3:.1f} тыс".replace(".", ",")
    return f"{value:.0f}"


def money(value: float) -> str:
    if not value:
        return "—"
    return format_money(value, CURRENCY, with_sign=False)


def _clothes_fallbacks(images: dict) -> dict[str, str]:
    """Первая доступная картинка для пары «пол + компонент + модель».

    Точного цвета может не быть, но лучше показать вещь другого цвета, чем
    пустой квадрат. В источнике часть вещей вообще без картинок (#4-82 и т.п.).
    """
    result: dict[str, str] = {}
    for key, url in images.items():
        if not isinstance(url, str):
            continue
        try:
            gender, rest = key.split(":", 1)
            component, drawable, _texture = rest[1:].split("-", 2)
        except ValueError:
            continue
        result.setdefault(f"{gender}:{component}:{drawable}", url)
    return result


def total_summary(entry: MarketEntry) -> tuple[str, str]:
    """«Количество на сервере»: сколько таких вещей вообще есть в игре.

    У одежды источник заполняет totalCount тем же числом, что и продажи,
    поэтому отдельного смысла там нет.
    """
    if entry.kind == "clothes":
        return "—", "источник не считает"
    if not entry.total:
        return "—", ""
    if not entry.sold:
        return f"{entry.total:,}".replace(",", " "), "нет продаж за 30 дн."
    percent = entry.sold / entry.total * 100
    hint = (
        "продано < 0,1%"
        if percent < 0.1
        else f"продано {percent:.1f}%".replace(".", ",")
    )
    return f"{entry.total:,}".replace(",", " "), hint


def day_dot(iso: str) -> str:
    if not iso:
        return "—"
    _, month, day = iso.split("-")
    return f"{day}.{month}"


def long_date(iso: str) -> str:
    if not iso:
        return ""
    year, month, day = (int(part) for part in iso.split("-"))
    return f"{day} {MONTHS[month - 1]} {year}"


def build_series(points: list[HistoryPoint], days: int = PERIOD_DAYS) -> list[dict]:
    """Ряд на 30 дней с пропусками и изменением 30-дневного объёма за сутки."""
    if not points:
        return []
    by_day = {point.day: point for point in points}
    last = date.fromisoformat(points[-1].day)
    series: list[dict] = []
    previous_sold: int | None = None

    for index in range(days - 1, -1, -1):
        day = (last - timedelta(days=index)).isoformat()
        point = by_day.get(day)
        if point is None:
            series.append(
                {"day": day, "empty": True, "avg": None, "min": None,
                 "max": None, "sold": None, "delta": None}
            )
            continue
        delta = None if previous_sold is None else point.sold - previous_sold
        series.append(
            {"day": day, "empty": False, "avg": point.avg, "min": point.min,
             "max": point.max, "sold": point.sold, "delta": delta}
        )
        previous_sold = point.sold
    return series


# ------------------------------------------------------------------------ service


class MarketService(QObject):
    """Загрузка открытых JSON m5rp с кэшем в памяти и на диске."""

    catalogReady = Signal(list, dict)
    catalogFailed = Signal(str)
    imageReady = Signal(str, QImage)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._manager = QNetworkAccessManager(self)
        self._json: dict[str, tuple[float, object]] = {}
        self._json_waiters: dict[str, list[tuple[object, object, object]]] = {}
        self._catalog_loading = False
        self._server_payload: dict | None = None
        self._images_payload: dict = {}
        self._images_failed = False
        self._image_cache: dict[str, QImage] = {}
        self._image_waiters: dict[str, list[object]] = {}
        self._image_failed: dict[str, float] = {}
        self._image_attempts: dict[str, int] = {}
        self._cache_dir = paths.data_dir() / "market"
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ catalog
    def load_catalog(self, force: bool = False) -> None:
        if self._catalog_loading:
            return
        self._catalog_loading = True
        if force:
            self._json.pop(CATALOG_URL, None)
            self._json.pop(IMAGES_URL, None)
        self._get_json(
            CATALOG_URL,
            CATALOG_TTL,
            self._on_server,
            self._on_catalog_error,
            force=force,
        )

    def _on_server(self, payload: object) -> None:
        if not isinstance(payload, dict):
            self._on_catalog_error("Некорректный ответ каталога")
            return
        self._server_payload = payload
        self._get_json(IMAGES_URL, IMAGES_TTL, self._on_images, self._on_images_error)

    def _on_images(self, payload: object) -> None:
        self._images_payload = payload if isinstance(payload, dict) else {}
        self._build_catalog()

    def _on_images_error(self, message: str) -> None:
        del message
        self._images_payload = {}
        self._images_failed = True
        self._build_catalog()

    def _on_catalog_error(self, message: str) -> None:
        self._catalog_loading = False
        self.catalogFailed.emit(message)

    def _build_catalog(self) -> None:
        payload = self._server_payload or {}
        images = self._images_payload
        fallbacks = _clothes_fallbacks(images)
        entries: list[MarketEntry] = []

        for item in payload.get("items") or []:
            ident = str(item.get("itemId"))
            name = str(item.get("itemName") or "")
            unnamed = not name or name.startswith("#")
            if unnamed:
                # у источника нет названия, вместо «#1276» показываем ID
                name = f"Предмет · ID {ident}"
            entries.append(
                MarketEntry(
                    key=f"{PREFIX}:items:{ident}",
                    kind="items",
                    ident=ident,
                    name=name,
                    image=f"{ITEM_IMAGE_BASE}/{ident}.webp",
                    sold=int(item.get("soldCount") or 0),
                    avg=float(item.get("averagePrice") or 0),
                    min=float(item.get("minPrice") or 0),
                    max=float(item.get("maxPrice") or 0),
                    total=int(item.get("totalCount") or 0),
                    unnamed=unnamed,
                )
            )

        for cloth in payload.get("clothes") or []:
            gender = int(cloth.get("gender") or 0)
            is_prop = int(cloth.get("isProp") or 0)
            component = int(cloth.get("component") or 0)
            drawable = int(cloth.get("drawable") or 0)
            texture = int(cloth.get("texture") or 0)
            group = f"{gender}:{component}:{drawable}"
            prefix = "P" if is_prop else "C"
            other = "C" if is_prop else "P"
            image = (
                images.get(f"{gender}:{prefix}{component}-{drawable}-{texture}")
                or images.get(f"{gender}:{other}{component}-{drawable}-{texture}")
                or fallbacks.get(group)
            )
            slot = cloth_slot(component, bool(is_prop))
            name = str(cloth.get("itemName") or "")
            unnamed = not name or name.startswith("#")
            # у официальной вики есть названия и картинки для части кастомных
            # вещей, которых нет в m5rp — используем их как дополнение
            wiki = WIKI_CLOTHES.get(
                f"{gender}:{int(is_prop)}:{component}:{drawable}:{texture}"
            )
            image_alt = None
            if wiki:
                if unnamed and wiki.get("name"):
                    name = wiki["name"]
                    unnamed = False
                if not image and wiki.get("image"):
                    image = wiki["image"]
                elif wiki.get("alt"):
                    # картинка m5rp может отдавать 404 — тогда берём вики
                    image_alt = wiki["alt"]
            if unnamed:
                # у источника нет названия: #<component>-<drawable>
                name = f"{slot} · модель {drawable} · цвет {texture}"
            entries.append(
                MarketEntry(
                    key=(
                        f"{PREFIX}:clothes:{gender}:{is_prop}:"
                        f"{component}:{drawable}:{texture}"
                    ),
                    kind="clothes",
                    ident=f"{drawable}/{texture}",
                    name=name,
                    image=image,
                    sold=int(cloth.get("soldCount") or 0),
                    avg=float(cloth.get("averagePrice") or 0),
                    min=float(cloth.get("minPrice") or 0),
                    max=float(cloth.get("maxPrice") or 0),
                    total=int(cloth.get("totalCount") or 0),
                    gender=gender,
                    texture=texture,
                    component=component,
                    drawable=drawable,
                    is_prop=bool(is_prop),
                    unnamed=unnamed,
                    group=group,
                    slot=slot,
                    image_alt=image_alt,
                )
            )

        for vehicle in payload.get("vehicleStatistics") or []:
            model = str(vehicle.get("model") or "")
            entries.append(
                MarketEntry(
                    key=f"{PREFIX}:vehicles:{model}",
                    kind="vehicles",
                    ident=model,
                    name=str(vehicle.get("modelName") or model or "Транспорт"),
                    image=f"{VEHICLE_IMAGE_BASE}/{model}.png" if model else None,
                    sold=int(vehicle.get("soldCount") or 0),
                    avg=float(vehicle.get("averagePrice") or 0),
                    min=float(vehicle.get("minPrice") or 0),
                    max=float(vehicle.get("maxPrice") or 0),
                    total=int(vehicle.get("totalCount") or 0),
                )
            )

        entries.sort(key=lambda entry: (-entry.sold, entry.name.lower()))

        meta = {
            "server": SERVER_LABEL,
            "updated": payload.get("lastUpdated")
            or payload.get("clothesLastUpdated")
            or payload.get("itemsLastUpdated")
            or None,
            "periodDays": int(payload.get("periodDays") or PERIOD_DAYS),
            "counts": {
                "clothes": len(payload.get("clothes") or []),
                "items": len(payload.get("items") or []),
                "vehicles": len(payload.get("vehicleStatistics") or []),
            },
        }

        self._catalog_loading = False
        self.catalogReady.emit(entries, meta)

    # ------------------------------------------------------------------ history
    def request_history(self, key: str, on_ok, on_error) -> None:
        bucket = bucket_of(key)
        url = f"{BASE}/public/data/history/{SERVER_ID}/{bucket}.json"

        def handle(payload: object) -> None:
            rows = None
            if isinstance(payload, dict):
                rows = (payload.get("data") or {}).get(key)
            points: list[HistoryPoint] = []
            for row in rows or []:
                if not isinstance(row, list) or not row:
                    continue
                day = str(row[0])
                if len(day) != 10 or day[4] != "-":
                    continue
                points.append(
                    HistoryPoint(
                        day=day,
                        avg=float(row[1] or 0) if len(row) > 1 else 0.0,
                        min=float(row[2] or 0) if len(row) > 2 else 0.0,
                        max=float(row[3] or 0) if len(row) > 3 else 0.0,
                        sold=int(row[4] or 0) if len(row) > 4 else 0,
                    )
                )
            points.sort(key=lambda point: point.day)
            on_ok(points)

        self._get_json(url, HISTORY_TTL, handle, on_error)

    # ------------------------------------------------------------------- images
    def request_image(self, url: str | None, callback) -> None:
        if not url:
            callback(QImage())
            return
        cached = self._image_cache.get(url)
        if cached is not None:
            callback(cached)
            return
        failed_at = self._image_failed.get(url)
        if failed_at is not None:
            if time.time() - failed_at < IMAGE_FAIL_TTL:
                callback(QImage())
                return
            self._image_failed.pop(url, None)

        waiters = self._image_waiters.setdefault(url, [])
        waiters.append(callback)
        if len(waiters) > 1:
            return
        self._start_image_request(url)

    def _start_image_request(self, url: str) -> None:
        request = QNetworkRequest(QUrl(url))
        request.setHeader(
            QNetworkRequest.KnownHeaders.UserAgentHeader, USER_AGENT
        )
        request.setRawHeader(
            b"Accept", b"image/avif,image/webp,image/png,image/*,*/*;q=0.8"
        )
        request.setTransferTimeout(20000)
        reply = self._manager.get(request)
        reply.finished.connect(lambda: self._on_image_reply(url, reply))

    def _on_image_reply(self, url: str, reply: QNetworkReply) -> None:
        image = QImage()
        if reply.error() == QNetworkReply.NetworkError.NoError:
            image.loadFromData(bytes(reply.readAll()))
        status = reply.attribute(
            QNetworkRequest.Attribute.HttpStatusCodeAttribute
        )
        reply.deleteLater()

        if not image.isNull():
            self._image_cache[url] = image
            self._image_failed.pop(url, None)
            self._image_attempts.pop(url, None)
            self._flush_image(url, image)
            return

        # 404/403 — картинки действительно нет; остальное чаще всего таймаут
        # или обрыв, поэтому пробуем ещё пару раз, не «запоминая» ошибку
        permanent = status in (403, 404)
        attempts = self._image_attempts.get(url, 0)
        if not permanent and attempts < 2:
            self._image_attempts[url] = attempts + 1
            QTimer.singleShot(
                IMAGE_RETRY_DELAY * (attempts + 1),
                lambda: self._start_image_request(url),
            )
            return

        self._image_failed[url] = time.time()
        self._image_attempts.pop(url, None)
        self._flush_image(url, image)

    def _flush_image(self, url: str, image: QImage) -> None:
        for callback in self._image_waiters.pop(url, []):
            try:
                callback(image)
            except RuntimeError:
                pass

    # --------------------------------------------------------------------- json
    def _get_json(
        self, url: str, ttl: float, on_ok, on_error, force: bool = False
    ) -> None:
        now = time.time()
        if not force:
            cached = self._json.get(url)
            if cached is not None and now - cached[0] <= ttl:
                on_ok(cached[1])
                return

            disk = self._disk_read(url, ttl)
            if disk is not None:
                self._json[url] = (now, disk)
                on_ok(disk)
                return

        # при обновлении всё равно держим старые данные на случай, если сеть
        # недоступна — тогда покажем их вместо ошибки
        stale = self._disk_read(url, float("inf")) if force else None

        waiters = self._json_waiters.setdefault(url, [])
        waiters.append((on_ok, on_error, stale))
        if len(waiters) > 1:
            return

        request = QNetworkRequest(QUrl(url))
        request.setHeader(
            QNetworkRequest.KnownHeaders.UserAgentHeader, USER_AGENT
        )
        request.setRawHeader(b"Referer", b"https://m5rp.ru/marketplace/")
        request.setRawHeader(b"Accept", b"application/json,text/plain,*/*")
        request.setTransferTimeout(30000)
        reply = self._manager.get(request)
        reply.finished.connect(lambda: self._on_json_reply(url, ttl, reply))

    def _on_json_reply(self, url: str, ttl: float, reply: QNetworkReply) -> None:
        waiters = self._json_waiters.pop(url, [])
        if reply.error() != QNetworkReply.NetworkError.NoError:
            status = reply.attribute(
                QNetworkRequest.Attribute.HttpStatusCodeAttribute
            )
            message = (
                f"Источник недоступен (HTTP {status})"
                if status
                else "Нет связи с m5rp.ru"
            )
            reply.deleteLater()
            for on_ok, on_error, stale in waiters:
                if stale is not None:
                    self._json[url] = (time.time(), stale)
                    on_ok(stale)
                else:
                    on_error(message)
            return

        raw = bytes(reply.readAll())
        reply.deleteLater()
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            for _on_ok, on_error, _stale in waiters:
                on_error("Не удалось разобрать ответ источника")
            return

        self._json[url] = (time.time(), payload)
        self._disk_write(url, payload)
        for on_ok, _on_error, _stale in waiters:
            on_ok(payload)

    # -------------------------------------------------------------------- cache
    def _cache_path(self, url: str) -> Path:
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:20]
        return self._cache_dir / f"{digest}.json"

    def _disk_read(self, url: str, ttl: float) -> object | None:
        path = self._cache_path(url)
        try:
            if not path.exists():
                return None
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return None
        if payload.get("url") != url:
            return None
        if time.time() - float(payload.get("ts") or 0) > ttl:
            return None
        return payload.get("data")

    def _disk_write(self, url: str, data: object) -> None:
        path = self._cache_path(url)
        tmp = path.with_suffix(".tmp")
        try:
            with tmp.open("w", encoding="utf-8") as handle:
                json.dump(
                    {"url": url, "ts": time.time(), "data": data},
                    handle,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            tmp.replace(path)
        except OSError:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass


# ------------------------------------------------------------------------- chart


class MarketChart(QWidget):
    """График: линия средней цены + столбцы 30-дневного объёма продаж."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(232)
        self.setMouseTracking(True)
        self._series: list[dict] = []
        self._accent = theme.DEFAULT_ACCENT
        self._hover: int | None = None
        self._message = ""

    def set_series(self, series: list[dict]) -> None:
        self._series = series
        self._hover = None
        self._message = ""
        self.update()

    def set_message(self, message: str) -> None:
        self._series = []
        self._hover = None
        self._message = message
        self.update()

    def set_accent(self, accent: str) -> None:
        self._accent = accent
        self.update()

    # ------------------------------------------------------------------- paint
    def _palette(self) -> dict[str, QColor]:
        light = theme.active_theme() == "light"
        accent = theme.theme_accent(self._accent, theme.active_theme())
        return {
            "text": QColor("#33383F" if light else "#D9DDE2"),
            "muted": QColor("#7A818B" if light else "#8C929A"),
            "grid": QColor(0, 0, 0, 16) if light else QColor(255, 255, 255, 18),
            "line": accent,
            "bar": QColor(accent.red(), accent.green(), accent.blue(), 60),
            "bar_edge": QColor(accent.red(), accent.green(), accent.blue(), 105),
            "tooltip": QColor(255, 255, 255, 246) if light else QColor(22, 25, 29, 246),
            "tooltip_edge": QColor(0, 0, 0, 30) if light else QColor(255, 255, 255, 34),
            "good": QColor("#1E8E4E" if light else "#67E396"),
            "bad": QColor("#C0392B" if light else "#FF8D8D"),
        }

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        colors = self._palette()

        if not self._series:
            painter.setPen(colors["muted"])
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(
                self.rect(), Qt.AlignmentFlag.AlignCenter, self._message
            )
            return

        width = self.width()
        height = self.height()
        left, right, top, bottom = 58.0, 44.0, 12.0, 26.0
        plot_w = max(1.0, width - left - right)
        plot_h = max(1.0, height - top - bottom)
        series = self._series
        step = plot_w / max(1, len(series) - 1)

        prices = [
            point["avg"] for point in series
            if not point["empty"] and point["avg"]
        ]
        if not prices:
            painter.setPen(colors["muted"])
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(
                self.rect(), Qt.AlignmentFlag.AlignCenter, "Нет цен за период"
            )
            return

        low = min(prices)
        high = max(prices)
        if high <= low:
            low = max(0.0, low * 0.9)
            high = high * 1.1 or 1.0
        else:
            span = high - low
            low = max(0.0, low - span * 0.12)
            high = high + span * 0.12

        sold_values = [
            point["sold"] or 0 for point in series if not point["empty"]
        ]
        max_sold = max(1, *sold_values) if sold_values else 1

        def x(index: int) -> float:
            return left + index * step

        def y_price(value: float) -> float:
            return top + (1 - (value - low) / (high - low)) * plot_h

        def y_sold(value: float) -> float:
            return top + (1 - value / (max_sold * 1.08)) * plot_h

        # ---------------------------------------------------- сетка и подписи
        grid_font = QFont("Segoe UI", 8)
        painter.setFont(grid_font)
        for index in range(5):
            value = low + (high - low) * index / 4
            y = y_price(value)
            painter.setPen(QPen(colors["grid"], 1, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(left, y), QPointF(width - right, y))
            painter.setPen(colors["muted"])
            painter.drawText(
                QRectF(0, y - 8, left - 8, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                compact(value),
            )

        painter.setPen(colors["muted"])
        for index in range(3):
            value = max_sold * index / 2
            y = y_sold(value)
            painter.drawText(
                QRectF(width - right + 8, y - 8, right - 6, 16),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                compact(value),
            )

        # ------------------------------------------------------------- столбцы
        bar_width = max(4.0, min(22.0, step * 0.55))
        painter.setPen(QPen(colors["bar_edge"], 1))
        painter.setBrush(colors["bar"])
        for index, point in enumerate(series):
            if point["empty"] or not point["sold"]:
                continue
            top_y = y_sold(point["sold"])
            rect = QRectF(
                x(index) - bar_width / 2,
                top_y,
                bar_width,
                max(0.0, height - bottom - top_y),
            )
            painter.drawRoundedRect(rect, 3.0, 3.0)

        # --------------------------------------------------------------- линия
        points: list[QPointF] = []
        for index, point in enumerate(series):
            if point["empty"] or not point["avg"]:
                continue
            points.append(QPointF(x(index), y_price(point["avg"])))
        if points:
            path = _smooth_path(points)
            area = QPainterPath(path)
            area.lineTo(points[-1].x(), height - bottom)
            area.lineTo(points[0].x(), height - bottom)
            area.closeSubpath()

            gradient = QLinearGradient(0, top, 0, height - bottom)
            accent = colors["line"]
            gradient.setColorAt(
                0.0, QColor(accent.red(), accent.green(), accent.blue(), 66)
            )
            gradient.setColorAt(
                1.0, QColor(accent.red(), accent.green(), accent.blue(), 4)
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(gradient)
            painter.drawPath(area)

            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(
                QPen(colors["line"], 2.2, Qt.PenStyle.SolidLine,
                     Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            )
            painter.drawPath(path)

            last = points[-1]
            painter.setBrush(colors["line"])
            painter.setPen(QPen(QColor("#0B0D10"), 2))
            painter.drawEllipse(last, 3.6, 3.6)

        # ------------------------------------------------------- подписи по X
        painter.setPen(colors["muted"])
        painter.setFont(grid_font)
        label_step = max(1, int(round(len(series) * 60 / plot_w)))
        indices = list(range(0, len(series), label_step))
        last = len(series) - 1
        if indices[-1] != last:
            if last - indices[-1] >= label_step or len(indices) == 1:
                indices.append(last)
            else:
                indices[-1] = last
        for index in indices:
            painter.drawText(
                QRectF(x(index) - 24, height - bottom + 6, 48, 16),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                day_dot(series[index]["day"]),
            )

        # ------------------------------------------------------------ курсор
        if self._hover is not None and 0 <= self._hover < len(series):
            point = series[self._hover]
            hx = x(self._hover)
            painter.setPen(
                QPen(colors["line"], 1, Qt.PenStyle.DashLine)
            )
            painter.drawLine(
                QPointF(hx, top), QPointF(hx, height - bottom)
            )
            if not point["empty"] and point["avg"]:
                painter.setBrush(colors["line"])
                painter.setPen(QPen(QColor("#0B0D10"), 2))
                painter.drawEllipse(
                    QPointF(hx, y_price(point["avg"])), 4.0, 4.0
                )
            self._paint_tooltip(painter, colors, point, hx)

    def _paint_tooltip(
        self, painter: QPainter, colors: dict[str, QColor], point: dict, hx: float
    ) -> None:
        box_w = 214.0
        box_h = 142.0
        left = hx + 14
        if left + box_w > self.width() - 6:
            left = hx - box_w - 14
        left = max(6.0, left)
        top = 8.0

        painter.setPen(QPen(colors["tooltip_edge"], 1))
        painter.setBrush(colors["tooltip"])
        painter.drawRoundedRect(QRectF(left, top, box_w, box_h), 9, 9)

        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(colors["muted"])
        painter.drawText(
            QRectF(left + 12, top + 8, box_w - 24, 16),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            long_date(point["day"]),
        )

        if point["empty"]:
            painter.setPen(colors["text"])
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(
                QRectF(left + 12, top + 30, box_w - 24, 40),
                Qt.AlignmentFlag.AlignLeft,
                "Нет данных за этот день",
            )
            return

        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        painter.setPen(colors["text"])
        painter.drawText(
            QRectF(left + 12, top + 26, box_w - 24, 22),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            money(point["avg"]),
        )

        rows = (
            ("Мин. за 30 дн.", money(point["min"] or 0), None),
            ("Макс. за 30 дн.", money(point["max"] or 0), None),
            ("Продажи за 30 дн.", f"{point['sold']:,}".replace(",", " "), None),
            ("Δ к пред. дню", _delta_text(point["delta"]), _delta_color(point["delta"], colors)),
        )
        y = top + 58
        painter.setFont(QFont("Segoe UI", 8))
        for caption, value, color in rows:
            painter.setPen(colors["muted"])
            painter.drawText(
                QRectF(left + 12, y, box_w - 100, 18),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                caption,
            )
            painter.setPen(color or colors["text"])
            painter.drawText(
                QRectF(left + box_w - 100, y, 88, 18),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                value,
            )
            y += 19

    # ------------------------------------------------------------------- hover
    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if not self._series:
            return
        left, right = 58.0, 44.0
        plot_w = max(1.0, self.width() - left - right)
        step = plot_w / max(1, len(self._series) - 1)
        if step <= 0:
            return
        index = int(round((event.position().x() - left) / step))
        index = max(0, min(len(self._series) - 1, index))
        if index != self._hover:
            self._hover = index
            self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        if self._hover is not None:
            self._hover = None
            self.update()
        super().leaveEvent(event)


def _delta_text(delta: int | None) -> str:
    if delta is None:
        return "—"
    if delta == 0:
        return "0"
    return f"{delta:+}".replace("+", "+ ").replace("-", "− ")


def _delta_color(delta: int | None, colors: dict[str, QColor]) -> QColor | None:
    if delta is None or delta == 0:
        return None
    return colors["good"] if delta > 0 else colors["bad"]


def _smooth_path(points: list[QPointF]) -> QPainterPath:
    path = QPainterPath()
    path.moveTo(points[0])
    if len(points) == 1:
        return path
    for index in range(len(points) - 1):
        p0 = points[index - 1] if index > 0 else points[index]
        p1 = points[index]
        p2 = points[index + 1]
        p3 = points[index + 2] if index + 2 < len(points) else p2
        c1 = QPointF(
            p1.x() + (p2.x() - p0.x()) / 6,
            p1.y() + (p2.y() - p0.y()) / 6,
        )
        c2 = QPointF(
            p2.x() - (p3.x() - p1.x()) / 6,
            p2.y() - (p3.y() - p1.y()) / 6,
        )
        path.cubicTo(c1, c2, p2)
    return path


# -------------------------------------------------------------------------- row


class MarketThumb(QLabel):
    """Миниатюра: по клику открывает картинку в полном размере."""

    clicked = Signal()

    def __init__(self, text: str, size: int) -> None:
        super().__init__(text)
        self.setObjectName("MarketThumb")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(size, size)
        self._zoomable = False
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def set_zoomable(self, zoomable: bool) -> None:
        self._zoomable = zoomable
        self.setCursor(
            Qt.CursorShape.PointingHandCursor
            if zoomable
            else Qt.CursorShape.ArrowCursor
        )
        self.setToolTip("Открыть картинку" if zoomable else "")

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._zoomable:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class MarketRow(QFrame):
    clicked = Signal(object)
    zoomRequested = Signal(object)

    def __init__(self, entry: MarketEntry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.entry = entry
        self.setObjectName("MarketRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(58)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(9, 7, 11, 7)
        layout.setSpacing(10)

        self._thumb = MarketThumb(entry.name[:1].upper(), 42)
        self._thumb.clicked.connect(
            lambda: self.zoomRequested.emit(self.entry)
        )
        layout.addWidget(self._thumb)

        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(2)
        name = ElidedLabel(entry.name)
        name.setObjectName("MarketName")
        name.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        info.addWidget(name)
        meta = QLabel(entry.subtitle)
        meta.setObjectName("MarketMeta")
        meta.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        info.addWidget(meta)
        layout.addLayout(info, 1)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(2)
        price = QLabel(money(entry.avg) if entry.avg else "нет цен")
        price.setObjectName("MarketPrice")
        price.setAlignment(Qt.AlignmentFlag.AlignRight)
        price.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        right.addWidget(price)
        sold = QLabel(f"{entry.sold:,} прод.".replace(",", " "))
        sold.setObjectName("MarketSold")
        sold.setAlignment(Qt.AlignmentFlag.AlignRight)
        sold.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )
        right.addWidget(sold)
        layout.addLayout(right)

    def set_image(self, image: QImage) -> None:
        if image.isNull():
            return
        pixmap = QPixmap.fromImage(
            image.scaled(
                84, 84,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        pixmap.setDevicePixelRatio(2.0)
        self._thumb.setText("")
        self._thumb.setPixmap(pixmap)
        self._thumb.set_zoomable(True)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.entry)
        super().mousePressEvent(event)


# ----------------------------------------------------------------------- detail


class MarketDetail(QWidget):
    backRequested = Signal()
    zoomRequested = Signal()
    tradeRequested = Signal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._entry: MarketEntry | None = None
        self._series: list[dict] = []
        self._stats: dict[str, tuple[QLabel, QLabel]] = {}
        self._thumb_pixmap: QPixmap | None = None
        self._image: QImage | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        self.back_button = QPushButton("← Назад к поиску")
        self.back_button.setObjectName("Ghost")
        self.back_button.setFixedHeight(30)
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_button.clicked.connect(self.backRequested.emit)
        top.addWidget(self.back_button, 0, Qt.AlignmentFlag.AlignLeft)
        top.addStretch(1)
        root.addLayout(top)

        scroll = QScrollArea()
        self.scroll_area = scroll
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.viewport().setAutoFillBackground(False)

        content = QWidget()
        content.setObjectName("HistoryContent")
        content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        body = QVBoxLayout(content)
        body.setContentsMargins(0, 0, 5, 4)
        body.setSpacing(10)

        # ---------------------------------------------------------------- шапка
        head = QFrame()
        head.setObjectName("MarketCard")
        head_layout = QHBoxLayout(head)
        head_layout.setContentsMargins(14, 13, 14, 13)
        head_layout.setSpacing(13)

        self._thumb = MarketThumb("?", 64)
        self._thumb.clicked.connect(self.zoomRequested.emit)
        head_layout.addWidget(self._thumb)

        titles = QVBoxLayout()
        titles.setContentsMargins(0, 0, 0, 0)
        titles.setSpacing(3)
        self._name = QLabel("—")
        self._name.setObjectName("MarketTitle")
        self._name.setWordWrap(True)
        titles.addWidget(self._name)
        self._sub = QLabel("")
        self._sub.setObjectName("MarketSub")
        titles.addWidget(self._sub)
        self._badges = QLabel("")
        self._badges.setObjectName("MarketMeta")
        titles.addWidget(self._badges)
        head_layout.addLayout(titles, 1)

        body.addWidget(head)
        body.addWidget(self._build_trade_card())

        # -------------------------------------------------------------- статы
        stats_grid = QGridLayout()
        stats_grid.setContentsMargins(0, 0, 0, 0)
        stats_grid.setHorizontalSpacing(8)
        stats_grid.setVerticalSpacing(8)
        for column, (key, caption) in enumerate(
            (
                ("avg", "Средняя цена"),
                ("min", "Минимальная"),
                ("max", "Максимальная"),
                ("sold", "Продано за 30 дн."),
                ("total", "Количество на сервере"),
                ("updated", "Обновлено"),
            )
        ):
            card = QFrame()
            card.setObjectName("MarketStat")
            card.setProperty("highlight", key == "avg")
            box = QVBoxLayout(card)
            box.setContentsMargins(11, 8, 11, 9)
            box.setSpacing(2)
            label = QLabel(caption)
            label.setObjectName("StatLabel")
            value = QLabel("—")
            value.setObjectName("StatValue")
            hint = QLabel("")
            hint.setObjectName("StatHint")
            box.addWidget(label)
            box.addWidget(value)
            box.addWidget(hint)
            stats_grid.addWidget(card, column // 3, column % 3)
            self._stats[key] = (value, hint)
        body.addLayout(stats_grid)

        # --------------------------------------------------------------- график
        chart_card = QFrame()
        chart_card.setObjectName("MarketCard")
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(14, 12, 14, 11)
        chart_layout.setSpacing(6)

        chart_head = QHBoxLayout()
        chart_head.setContentsMargins(0, 0, 0, 0)
        chart_titles = QVBoxLayout()
        chart_titles.setSpacing(1)
        chart_title = QLabel("Цена с маркетплейса")
        chart_title.setObjectName("MarketCardTitle")
        chart_titles.addWidget(chart_title)
        chart_sub = QLabel("Средняя цена и объём продаж в 30-дневном окне на дату")
        chart_sub.setObjectName("MarketSub")
        chart_titles.addWidget(chart_sub)
        chart_head.addLayout(chart_titles, 1)
        self._updated = QLabel("—")
        self._updated.setObjectName("MarketUpdated")
        chart_head.addWidget(self._updated, 0, Qt.AlignmentFlag.AlignTop)
        chart_layout.addLayout(chart_head)

        self.chart = MarketChart()
        chart_layout.addWidget(self.chart)

        hint = QLabel(
            "Каждая точка — 30 дней, заканчивающиеся этой датой. Средняя — средняя "
            "цена всех продаж окна, минимум и максимум — крайние цены среди них, "
            "поэтому разброс вокруг средней бывает большим."
        )
        hint.setObjectName("MarketHint")
        hint.setWordWrap(True)
        chart_layout.addWidget(hint)
        body.addWidget(chart_card)

        # --------------------------------------------------------------- таблица
        table_card = QFrame()
        table_card.setObjectName("MarketCard")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(14, 12, 14, 12)
        table_layout.setSpacing(8)

        table_head = QHBoxLayout()
        table_title = QLabel("Статистика по дням")
        table_title.setObjectName("MarketCardTitle")
        table_head.addWidget(table_title)
        table_head.addStretch(1)
        table_note = QLabel("Окно 30 дней · Δ — изменение за сутки")
        table_note.setObjectName("MarketUpdated")
        table_head.addWidget(table_note)
        table_layout.addLayout(table_head)

        self._table = QGridLayout()
        self._table.setContentsMargins(0, 0, 0, 0)
        self._table.setHorizontalSpacing(10)
        self._table.setVerticalSpacing(4)
        table_layout.addLayout(self._table)

        self._note = QLabel("")
        self._note.setObjectName("MarketHint")
        self._note.setWordWrap(True)
        table_layout.addWidget(self._note)

        body.addWidget(table_card)
        body.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

    # ------------------------------------------------------------------ trade
    def _build_trade_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("TradeCard")
        box = QVBoxLayout(card)
        box.setContentsMargins(14, 12, 14, 12)
        box.setSpacing(8)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(10)
        titles = QVBoxLayout()
        titles.setSpacing(1)
        title = QLabel("Сделка по предмету")
        title.setObjectName("MarketCardTitle")
        titles.addWidget(title)
        sub = QLabel(
            "Цена, количество и комментарий — можно изменить; "
            "фото подставится из маркета"
        )
        sub.setObjectName("MarketSub")
        sub.setWordWrap(True)
        titles.addWidget(sub)
        top.addLayout(titles, 1)

        self._trade_sum = QLabel("Сумма: —")
        self._trade_sum.setObjectName("TradeSum")
        self._trade_sum.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._trade_sum.setToolTip("Итоговая сумма сделки: цена × количество")
        top.addWidget(self._trade_sum, 0, Qt.AlignmentFlag.AlignTop)
        box.addLayout(top)

        side_row = QHBoxLayout()
        side_row.setContentsMargins(0, 0, 0, 0)
        side_row.setSpacing(6)
        self._trade_buy = QPushButton("Купил")
        self._trade_sell = QPushButton("Продал")
        for button in (self._trade_buy, self._trade_sell):
            button.setObjectName("TradeSide")
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFixedHeight(32)
            button.clicked.connect(self._update_trade_preview)
            side_row.addWidget(button)
        self._trade_buy.setChecked(True)
        side_row.addStretch(1)
        box.addLayout(side_row)

        fields = QHBoxLayout()
        fields.setContentsMargins(0, 0, 0, 0)
        fields.setSpacing(10)

        price_box = QVBoxLayout()
        price_box.setSpacing(4)
        price_label = QLabel("Цена за 1 шт.")
        price_label.setObjectName("StatLabel")
        price_box.addWidget(price_label)
        self._trade_price = AmountLineEdit()
        self._trade_price.setFixedHeight(38)
        self._trade_price.setPlaceholderText("Например: 1.250")
        self._trade_price.textChanged.connect(self._update_trade_preview)
        self._trade_price.returnPressed.connect(self._on_trade_submit)
        price_box.addWidget(self._trade_price)
        fields.addLayout(price_box, 1)

        qty_box = QVBoxLayout()
        qty_box.setSpacing(4)
        qty_label = QLabel("Кол-во")
        qty_label.setObjectName("StatLabel")
        qty_label.setToolTip("Сколько штук куплено или продано")
        qty_box.addWidget(qty_label)
        self._trade_qty = QLineEdit("1")
        self._trade_qty.setFixedHeight(38)
        self._trade_qty.setFixedWidth(84)
        self._trade_qty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._trade_qty.setValidator(QIntValidator(1, 9999, self))
        self._trade_qty.setToolTip("Сколько штук куплено или продано")
        self._trade_qty.textChanged.connect(self._update_trade_preview)
        self._trade_qty.returnPressed.connect(self._on_trade_submit)
        qty_box.addWidget(self._trade_qty)
        fields.addLayout(qty_box, 0)
        box.addLayout(fields)

        quick_row = QHBoxLayout()
        quick_row.setContentsMargins(0, 0, 0, 0)
        quick_row.setSpacing(5)
        quick_hint = QLabel("Подставить цену:")
        quick_hint.setObjectName("StatLabel")
        quick_row.addWidget(quick_hint)
        self._trade_quick: dict[str, QPushButton] = {}
        for key, caption in (
            ("avg", "Средняя"),
            ("min", "Мин."),
            ("max", "Макс."),
        ):
            button = QPushButton(caption)
            button.setObjectName("TradeQuick")
            button.setFixedHeight(24)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda _checked=False, k=key: self._fill_trade_price(k)
            )
            quick_row.addWidget(button)
            self._trade_quick[key] = button
        quick_row.addStretch(1)
        box.addLayout(quick_row)

        self._trade_comment = QLineEdit()
        self._trade_comment.setFixedHeight(34)
        self._trade_comment.setPlaceholderText(
            "Комментарий к сделке (не обязательно)"
        )
        self._trade_comment.returnPressed.connect(self._on_trade_submit)
        box.addWidget(self._trade_comment)

        self._trade_delta = QLabel(
            "Введите цену — покажу разницу со средней рыночной"
        )
        self._trade_delta.setObjectName("TradeDelta")
        self._trade_delta.setWordWrap(True)
        box.addWidget(self._trade_delta)
        self._trade_verdict = QLabel("")
        self._trade_verdict.setObjectName("TradeVerdict")
        self._trade_verdict.setWordWrap(True)
        box.addWidget(self._trade_verdict)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.setSpacing(10)
        self._trade_own = ElidedLabel("")
        self._trade_own.setObjectName("TradeOwn")
        bottom.addWidget(self._trade_own, 1)
        self._trade_submit = QPushButton("Внести сделку")
        self._trade_submit.setObjectName("Submit")
        self._trade_submit.setFixedHeight(38)
        self._trade_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        self._trade_submit.clicked.connect(self._on_trade_submit)
        bottom.addWidget(self._trade_submit, 0)
        box.addLayout(bottom)

        self._trade_saved = QLabel("")
        self._trade_saved.setObjectName("TradeSaved")
        self._trade_saved.setWordWrap(True)
        self._trade_saved.hide()
        box.addWidget(self._trade_saved)
        return card

    def _trade_side(self) -> str:
        return "sell" if self._trade_sell.isChecked() else "buy"

    @staticmethod
    def _number_text(value: float) -> str:
        if abs(value - round(value)) < 0.005:
            return str(int(round(value)))
        return f"{value:.2f}".replace(".", ",")

    def _trade_quantity(self) -> int:
        try:
            value = int(self._trade_qty.text().strip())
        except ValueError:
            return 1
        return max(1, min(9999, value))

    def _fill_trade_price(self, key: str) -> None:
        entry = self._entry
        if entry is None:
            return
        value = {
            "avg": entry.avg,
            "min": entry.min,
            "max": entry.max,
        }.get(key) or 0.0
        if value <= 0:
            return
        self._trade_price.setText(self._number_text(value))
        self._trade_price.setFocus()
        self._trade_price.selectAll()

    def _update_trade_preview(self) -> None:
        entry = self._entry
        price = parse_amount(self._trade_price.text())
        quantity = self._trade_quantity()
        amount = (price or 0.0) * quantity
        self._trade_saved.hide()
        self._trade_sum.setText(
            f"Сумма: {format_money(amount, CURRENCY, with_sign=False)}"
            if price
            else "Сумма: —"
        )

        if entry is None:
            return

        for key, value in (
            ("avg", entry.avg),
            ("min", entry.min),
            ("max", entry.max),
        ):
            button = self._trade_quick[key]
            button.setEnabled(value > 0)
            button.setToolTip(
                f"Подставить: {money(value)}" if value else "Нет данных"
            )
        self._trade_quick["avg"].setText(
            f"Средняя · {compact(entry.avg)}" if entry.avg else "Средняя"
        )
        self._trade_quick["min"].setText(
            f"Мин. · {compact(entry.min)}" if entry.min else "Мин."
        )
        self._trade_quick["max"].setText(
            f"Макс. · {compact(entry.max)}" if entry.max else "Макс."
        )

        if price is None:
            state = "flat"
            self._trade_delta.setText(
                "Введите цену — покажу разницу со средней рыночной"
            )
            self._trade_verdict.setText(
                f"Средняя за 30 дней: {money(entry.avg)}" if entry.avg else ""
            )
        elif not entry.avg:
            state = "flat"
            self._trade_delta.setText(
                "У источника нет средней цены — сравнивать не с чем"
            )
            self._trade_verdict.setText("")
        else:
            delta = price - entry.avg
            percent = delta / entry.avg * 100.0
            side = self._trade_side()
            if abs(percent) < 0.5:
                state = "flat"
                verdict = "на уровне средней"
            elif (side == "buy") == (delta < 0):
                state = "good"
                verdict = (
                    "дешевле средней — выгодная покупка"
                    if side == "buy"
                    else "дороже средней — выгодная продажа"
                )
            else:
                state = "bad"
                verdict = (
                    "дороже средней — переплата"
                    if side == "buy"
                    else "дешевле средней — недополучите"
                )
            sign = "+" if delta > 0 else "−" if delta < 0 else ""
            percent_text = f"{abs(percent):.1f}".replace(".", ",")
            diff_text = format_money(abs(delta), CURRENCY, with_sign=False)
            self._trade_delta.setText(
                f"{sign}{percent_text}% от средней · {sign}{diff_text}"
            )
            self._trade_verdict.setText(
                f"{verdict.capitalize()} · средняя за 30 дней {money(entry.avg)}"
            )

        self._trade_delta.setProperty("state", state)
        repolish(self._trade_delta)

    def _on_trade_submit(self) -> None:
        entry = self._entry
        if entry is None:
            return
        price = parse_amount(self._trade_price.text())
        if price is None:
            self._trade_price.setProperty("error", True)
            repolish(self._trade_price)
            self._trade_saved.setText("Укажите цену за 1 шт.")
            self._trade_saved.setProperty("state", "error")
            repolish(self._trade_saved)
            self._trade_saved.show()
            self._trade_price.setFocus()
            return

        self._trade_price.setProperty("error", False)
        repolish(self._trade_price)
        quantity = self._trade_quantity()
        if self._trade_qty.text().strip() != str(quantity):
            self._trade_qty.setText(str(quantity))
        payload = {
            "product": entry.name,
            "kind": entry.kind,
            "key": entry.key,
            "side": self._trade_side(),
            "price": price,
            "quantity": quantity,
            "amount": price * quantity,
            "comment": self._trade_comment.text().strip(),
            "category": KIND_CATEGORY.get(entry.kind, "transport"),
            "photo": image_to_jpeg(self._image) if self._image is not None else b"",
        }
        self.tradeRequested.emit(payload)
        self._trade_comment.clear()

    def set_trade_saved(self, payload: dict) -> None:
        side = str(payload.get("side") or "buy")
        quantity = max(1, int(payload.get("quantity") or 1))
        price = float(payload.get("price") or 0.0)
        amount = float(payload.get("amount") or 0.0)
        word = "купил" if side == "buy" else "продал"
        price_text = (
            f"{quantity} шт. × {money(price)}"
            if quantity > 1
            else money(price)
        )
        self._trade_saved.setText(
            f"Внесено в историю: {word} {price_text} · "
            f"{format_money(amount, CURRENCY, with_sign=False)}"
        )
        self._trade_saved.setProperty("state", "ok")
        repolish(self._trade_saved)
        self._trade_saved.show()

    def set_own_stats(
        self,
        buy_count: int,
        buy_average: float | None,
        sell_count: int,
        sell_average: float | None,
    ) -> None:
        parts: list[str] = []
        if buy_count:
            parts.append(f"покупки: {buy_count} × {money(buy_average or 0)}")
        if sell_count:
            parts.append(f"продажи: {sell_count} × {money(sell_average or 0)}")
        text = (
            "Мои сделки за 30 дней — " + " · ".join(parts)
            if parts
            else "Моих сделок с этим предметом пока нет"
        )
        self._trade_own.set_full_text(text)

    # ------------------------------------------------------------------- data
    def set_entry(self, entry: MarketEntry) -> None:
        self._entry = entry
        self._image = None
        self._thumb_pixmap = None
        self._thumb.set_zoomable(False)
        self._thumb.setText(entry.name[:1].upper())
        self._thumb.setPixmap(QPixmap())
        self._name.setText(entry.name)
        self._sub.setText(entry.subtitle)
        self._badges.setText(
            f"{entry.sold:,} продаж за 30 дней".replace(",", " ")
            if entry.sold else "нет продаж за 30 дней"
        )
        self._set_stat("avg", money(entry.avg), "за 30 дней" if entry.avg else "")
        self._set_stat("min", money(entry.min), "за 30 дней" if entry.min else "")
        self._set_stat("max", money(entry.max), "за 30 дней" if entry.max else "")
        self._set_stat(
            "sold",
            f"{entry.sold:,}".replace(",", " ") + " шт.",
            f"≈ {entry.sold / PERIOD_DAYS:.1f} в день".replace(".", ",")
            if entry.sold else "нет продаж",
        )
        total_value, total_hint = total_summary(entry)
        self._set_stat("total", total_value, total_hint)
        self._set_stat("updated", "—", "")
        self._updated.setText("—")
        self.chart.set_message("Загружаем историю…")
        self._clear_table()
        self._table_note("")
        self._trade_price.setProperty("error", False)
        repolish(self._trade_price)
        self._trade_price.clear()
        self._trade_comment.clear()
        self._trade_saved.hide()
        self._trade_saved.setProperty("state", "ok")
        self._trade_own.set_full_text("")
        self._update_trade_preview()

    def set_image(self, image: QImage) -> None:
        if image.isNull():
            return
        self._image = QImage(image)
        pixmap = QPixmap.fromImage(
            image.scaled(
                128, 128,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        pixmap.setDevicePixelRatio(2.0)
        self._thumb_pixmap = pixmap
        self._thumb.setText("")
        self._thumb.setPixmap(pixmap)
        self._thumb.set_zoomable(True)

    def set_points(self, points: list[HistoryPoint]) -> None:
        entry = self._entry
        if entry is None:
            return
        self._series = build_series(points)
        if not points:
            self.chart.set_message("По этому предмету пока нет дневной истории")
            self._updated.setText("—")
            self._set_stat("updated", "—", "")
            self._clear_table()
            self._table_note(
                "Источник ещё не накопил историю по этому предмету."
            )
            return

        latest = points[-1]
        self._updated.setText(f"обновлено {day_dot(latest.day)}")
        self._set_stat(
            "avg", money(latest.avg), f"за {PERIOD_DAYS} дней"
        )
        self._set_stat("min", money(latest.min), "за 30 дней" if latest.min else "")
        self._set_stat("max", money(latest.max), "за 30 дней" if latest.max else "")
        self._set_stat(
            "sold",
            f"{latest.sold:,}".replace(",", " ") + " шт.",
            f"≈ {latest.sold / PERIOD_DAYS:.1f} в день".replace(".", ",")
            if latest.sold else "нет продаж",
        )
        self._set_stat("updated", day_dot(latest.day), f"{len(points)} дней данных")
        self.chart.set_series(self._series)
        self._fill_table(self._series)
        self._table_note(
            f"{len(points)} из {PERIOD_DAYS} дней с данными · "
            f"{long_date(points[0].day)} — {long_date(latest.day)}"
        )

    def set_error(self, message: str) -> None:
        self.chart.set_message("Не удалось загрузить историю")
        self._clear_table()
        self._table_note(message)

    def refresh_theme(self, accent: str) -> None:
        self.chart.set_accent(accent)

    # ------------------------------------------------------------------ stats
    def _set_stat(self, key: str, value: str, hint: str) -> None:
        pair = self._stats.get(key)
        if pair is None:
            return
        pair[0].setText(value)
        pair[1].setText(hint)
        pair[1].setVisible(bool(hint))

    # ------------------------------------------------------------------ table
    def _clear_table(self) -> None:
        while self._table.count():
            item = self._table.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _table_note(self, text: str) -> None:
        self._note.setText(text)
        self._note.setVisible(bool(text))

    def _fill_table(self, series: list[dict]) -> None:
        self._clear_table()
        headers = ("Дата", "За 30 дн.", "Δ", "Средняя", "Мин.", "Макс.")
        for column, text in enumerate(headers):
            label = QLabel(text)
            label.setObjectName("TableHead")
            label.setAlignment(
                Qt.AlignmentFlag.AlignLeft
                if column == 0
                else Qt.AlignmentFlag.AlignRight
            )
            self._table.addWidget(label, 0, column)

        row = 1
        for point in reversed(series):
            if point["empty"]:
                continue
            values = (
                day_dot(point["day"]),
                f"{point['sold']:,}".replace(",", " "),
                _delta_text(point["delta"]),
                money(point["avg"] or 0),
                money(point["min"] or 0),
                money(point["max"] or 0),
            )
            for column, text in enumerate(values):
                label = QLabel(text)
                label.setObjectName("TableCellStrong" if column in (0, 1) else "TableCell")
                label.setAlignment(
                    Qt.AlignmentFlag.AlignLeft
                    if column == 0
                    else Qt.AlignmentFlag.AlignRight
                )
                if column == 2:
                    delta = point["delta"]
                    if delta:
                        label.setProperty("state", "up" if delta > 0 else "down")
                self._table.addWidget(label, row, column)
            row += 1

        for column in range(6):
            self._table.setColumnStretch(column, 2 if column in (3, 4, 5) else 1)


# ------------------------------------------------------------------------- panel


class MarketPanel(QWidget):
    """Вкладка «Маркет»: поиск по каталогу и карточка предмета с графиком."""

    imageRequested = Signal(QImage, str)
    tradeRequested = Signal(dict)
    tradePhotoReady = Signal(int, bytes)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = MarketService(self)
        self.stats_provider = None
        self._entries: list[MarketEntry] = []
        self._meta: dict = {}
        self._kind = "clothes"
        self._query = ""
        self._limit = PAGE_SIZE
        self._current: MarketEntry | None = None
        self._rows: list[MarketRow] = []
        self._visible: list[MarketEntry] = []
        self._rendered = 0
        self._loading = False
        self._accent = theme.DEFAULT_ACCENT

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(150)
        self._search_timer.timeout.connect(self._apply_search)

        self._build_ui()
        self.service.catalogReady.connect(self._on_catalog)
        self.service.catalogFailed.connect(self._on_catalog_error)

    # --------------------------------------------------------------------- ui
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(9)

        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.addStretch(1)

        self.search = QLineEdit()
        self.search.setFixedHeight(40)
        self.search.setFixedWidth(400)
        self.search.setPlaceholderText("Поиск: перчатки, BMW, патроны…")
        self.search.setClearButtonEnabled(True)
        self._search_action = self.search.addAction(
            icons.icon("search", theme.icon_tone("muted")),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        self.search.textChanged.connect(self._on_search_text)
        search_row.addWidget(self.search)

        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.setObjectName("Ghost")
        self.refresh_button.setFixedHeight(40)
        self.refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_button.setToolTip("Заново загрузить данные с m5rp.ru")
        self.refresh_button.clicked.connect(self._reload)
        search_row.addWidget(self.refresh_button)

        search_row.addStretch(1)
        root.addLayout(search_row)

        chips_row = QHBoxLayout()
        chips_row.setContentsMargins(0, 0, 0, 0)
        chips_row.setSpacing(4)
        self._kind_buttons: dict[str, QPushButton] = {}
        for key in ("clothes", "items", "vehicles"):
            button = QPushButton(KIND_LABEL[key])
            button.setObjectName("Tab")
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _c=False, k=key: self._select_kind(k))
            self._kind_buttons[key] = button
            chips_row.addWidget(button)
        self._kind_buttons[self._kind].setChecked(True)
        chips_row.addStretch(1)

        self._source_label = QLabel(SERVER_LABEL)
        self._source_label.setObjectName("MarketUpdated")
        chips_row.addWidget(self._source_label, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(chips_row)

        self._status = QLabel("")
        self._status.setObjectName("MarketStatus")
        self._status.setWordWrap(True)
        self._status.hide()
        root.addWidget(self._status)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_list_page())
        self.detail = MarketDetail()
        self.detail.backRequested.connect(self._show_list)
        self.detail.zoomRequested.connect(self._zoom_current)
        self.detail.tradeRequested.connect(self.tradeRequested.emit)
        self.stack.addWidget(self.detail)
        root.addWidget(self.stack, 1)

    def _build_list_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll.viewport().setAutoFillBackground(False)

        self._rows_host = QWidget()
        self._rows_host.setObjectName("HistoryContent")
        self._rows_host.setAttribute(
            Qt.WidgetAttribute.WA_StyledBackground, True
        )
        self._rows_layout = QVBoxLayout(self._rows_host)
        self._rows_layout.setContentsMargins(0, 0, 5, 0)
        self._rows_layout.setSpacing(6)
        self._rows_layout.addStretch(1)
        self.scroll.setWidget(self._rows_host)
        layout.addWidget(self.scroll, 1)

        self.more_button = QPushButton("Показать ещё")
        self.more_button.setObjectName("Ghost")
        self.more_button.setFixedHeight(34)
        self.more_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.more_button.clicked.connect(self._show_more)
        self.more_button.hide()
        layout.addWidget(self.more_button)
        return page

    # ------------------------------------------------------------------ sort
    def _filtered(self) -> list[MarketEntry]:
        query = self._query.lower()
        entries = [entry for entry in self._entries if entry.kind == self._kind]
        if query:
            entries = [entry for entry in entries if query in entry.name.lower()]
            entries.sort(
                key=lambda entry: (
                    not entry.name.lower().startswith(query),
                    -entry.sold,
                    entry.name.lower(),
                )
            )
        else:
            entries.sort(key=lambda entry: (-entry.sold, entry.name.lower()))
        return entries

    def _on_search_text(self, text: str) -> None:
        self._pending_query = text
        self._search_timer.start()

    def _apply_search(self) -> None:
        self._query = getattr(self, "_pending_query", self.search.text()).strip()
        self._limit = PAGE_SIZE
        self._show_list()
        self._render_rows()

    def _select_kind(self, kind: str) -> None:
        if kind == self._kind:
            return
        self._kind = kind
        self._kind_buttons[kind].setChecked(True)
        self._limit = PAGE_SIZE
        self._show_list()
        self._render_rows()

    def _show_more(self) -> None:
        if self._limit >= len(self._visible):
            return
        self._limit += PAGE_SIZE
        target = min(self._limit, len(self._visible))
        self._append_rows(self._visible[self._rendered : target])
        self._update_more_button()

    def ensure_loaded(self) -> None:
        if self._entries or self._loading:
            return
        self._reload(force=False)

    def _reload(self, force: bool = True) -> None:
        if self._loading:
            return
        self._loading = True
        self._status.setText("Загружаем каталог с m5rp.ru…")
        self._status.setProperty("state", "")
        repolish(self._status)
        self._status.show()
        self.more_button.hide()
        self._clear_rows()
        self.service.load_catalog(force=force)

    # ----------------------------------------------------------------- catalog
    def _on_catalog(self, entries: list, meta: dict) -> None:
        self._loading = False
        self._entries = list(entries)
        self._meta = meta or {}
        self._status.hide()
        updated = str(self._meta.get("updated") or "")
        day = updated[8:10] + "." + updated[5:7] if len(updated) >= 10 else ""
        self._source_label.setText(
            f"{SERVER_LABEL}" + (f" · обновлено {day}" if day else "")
        )
        self._source_label.setToolTip(
            "Данные m5rp.ru за 30 дней (обновление раз в сутки)"
        )
        self._render_rows()

    def _on_catalog_error(self, message: str) -> None:
        self._loading = False
        self._status.setText(f"Не удалось загрузить каталог: {message}")
        self._status.setProperty("state", "error")
        repolish(self._status)
        self._status.show()
        self._clear_rows()
        self.more_button.hide()

    # -------------------------------------------------------------------- rows
    def _clear_rows(self) -> None:
        self._rows = []
        self._rendered = 0
        while self._rows_layout.count() > 1:
            item = self._rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()

    def _render_rows(self) -> None:
        entries = self._filtered()
        self._visible = entries
        self._clear_rows()

        if not entries:
            message = (
                "Ничего не найдено — попробуйте другое название"
                if self._query
                else "На этом сервере пока нет продаж в выбранном разделе"
            )
            self._status.setText(message)
            self._status.setProperty("state", "")
            repolish(self._status)
            self._status.show()
            self.more_button.hide()
            return

        self._status.hide()
        self._append_rows(entries[: self._limit])
        self._update_more_button()
        self._rows_layout.activate()
        self._rows_host.updateGeometry()
        self.scroll.verticalScrollBar().setValue(0)

    def _append_rows(self, entries: list[MarketEntry]) -> None:
        for entry in entries:
            row = MarketRow(entry)
            row.clicked.connect(self._open_entry)
            row.zoomRequested.connect(self._zoom_entry)
            self._rows_layout.insertWidget(self._rows_layout.count() - 1, row)
            self._rows.append(row)
            self._load_image(entry.image, row.set_image, entry.image_alt)
        self._rendered = len(self._rows)
        self._rows_layout.activate()
        self._rows_host.updateGeometry()

    def _update_more_button(self) -> None:
        remaining = len(self._visible) - self._rendered
        self.more_button.setVisible(remaining > 0)
        self.more_button.setText(
            f"Показать ещё ({remaining})" if remaining > 0 else "Показать ещё"
        )

    def _load_image(self, url: str | None, setter, alt: str | None = None) -> None:
        def apply(image: QImage) -> None:
            if image.isNull() and alt:
                self.service.request_image(
                    alt, lambda second: self._apply_image(setter, second)
                )
                return
            self._apply_image(setter, image)

        self.service.request_image(url, apply)

    @staticmethod
    def _apply_image(setter, image: QImage) -> None:
        try:
            setter(image)
        except RuntimeError:
            pass

    # ------------------------------------------------------------------ detail
    def _open_entry(self, entry: MarketEntry) -> None:
        self._search_timer.stop()
        self._current = entry
        self.detail.set_entry(entry)
        self._refresh_own_stats()
        self.stack.setCurrentWidget(self.detail)
        self._load_image(entry.image, self.detail.set_image, entry.image_alt)

        def on_ok(points: list[HistoryPoint]) -> None:
            if self._current is not entry:
                return
            self.detail.set_points(points)

        def on_error(message: str) -> None:
            if self._current is not entry:
                return
            self.detail.set_error(message)

        self.service.request_history(entry.key, on_ok, on_error)

    def _zoom_entry(self, entry: MarketEntry) -> None:
        if not entry.image and not entry.image_alt:
            return

        def show(image: QImage) -> None:
            if image.isNull() and entry.image_alt:
                self.service.request_image(entry.image_alt, show_alt)
                return
            if not image.isNull():
                self.imageRequested.emit(image, entry.name)

        def show_alt(image: QImage) -> None:
            if not image.isNull():
                self.imageRequested.emit(image, entry.name)

        self.service.request_image(entry.image, show)

    def _zoom_current(self) -> None:
        entry = self._current
        if entry is not None:
            self._zoom_entry(entry)

    # ------------------------------------------------------------------- trade
    def set_stats_provider(self, provider) -> None:
        """Callback ``(product, kind) -> (buy_count, buy_avg, sell_count, sell_avg)``."""
        self.stats_provider = provider

    def _refresh_own_stats(self) -> None:
        entry = self._current
        if entry is None or self.stats_provider is None:
            return
        try:
            data = self.stats_provider(entry.name, entry.kind)
        except Exception:  # noqa: BLE001
            return
        if entry is not self._current:
            return
        self.detail.set_own_stats(*data)

    def notify_trade_saved(self, payload: dict, deal_id: int) -> None:
        self.detail.set_trade_saved(payload)
        self._refresh_own_stats()
        if payload.get("photo"):
            return
        entry = self._entry_by_key(str(payload.get("key") or "")) or self._current
        if entry is not None:
            self._request_trade_photo(entry, deal_id)

    def _entry_by_key(self, key: str) -> MarketEntry | None:
        for entry in self._entries:
            if entry.key == key:
                return entry
        return None

    def _request_trade_photo(
        self, entry: MarketEntry, deal_id: int
    ) -> None:
        """Фото предмета не успело загрузиться к моменту сделки — догружаем."""

        def finish(image: QImage) -> None:
            if image.isNull():
                return
            data = image_to_jpeg(image)
            if data:
                self.tradePhotoReady.emit(deal_id, data)

        def apply(image: QImage) -> None:
            if image.isNull() and entry.image_alt:
                self.service.request_image(entry.image_alt, finish)
                return
            finish(image)

        self.service.request_image(entry.image, apply)

    def _show_list(self) -> None:
        self._current = None
        self.stack.setCurrentIndex(0)
        self.search.setFocus()

    # ------------------------------------------------------------------- theme
    def refresh_theme(self, accent: str) -> None:
        self._accent = accent
        self._search_action.setIcon(
            icons.icon("search", theme.icon_tone("muted"))
        )
        self.detail.refresh_theme(accent)
        for row in self._rows:
            row.update()
