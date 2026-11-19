from __future__ import annotations

import math
import struct
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)

from .paths import data_dir, resource_path

ICON_CANVAS = 72  # rendered larger, Qt downscales smoothly
DEFAULT_ICON_COLOR = "#C3C8CF"
BRAND_ICON = ("assets", "galardo.png")


# --------------------------------------------------------------------------- drawings
def _draw_search(p: QPainter) -> None:
    p.drawEllipse(QRectF(3.5, 3.5, 12.6, 12.6))
    p.drawLine(15.0, 15.0, 20.2, 20.2)


def _draw_calendar(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(3.0, 5.0, 18.0, 15.0), 2.8, 2.8)
    p.drawLine(3.4, 9.4, 20.6, 9.4)
    p.drawLine(7.6, 2.8, 7.6, 6.5)
    p.drawLine(16.4, 2.8, 16.4, 6.5)


def _draw_refresh(p: QPainter) -> None:
    p.drawArc(QRectF(4.2, 4.2, 15.6, 15.6), 40 * 16, 285 * 16)
    p.drawLine(17.9, 6.9, 14.6, 7.4)
    p.drawLine(17.9, 6.9, 17.6, 10.3)


def _draw_trash(p: QPainter) -> None:
    p.drawLine(4.0, 6.6, 20.0, 6.6)
    p.drawLine(9.2, 6.4, 9.2, 4.2)
    p.drawLine(9.2, 4.2, 14.8, 4.2)
    p.drawLine(14.8, 4.2, 14.8, 6.4)
    p.drawRoundedRect(QRectF(6.0, 6.6, 12.0, 14.0), 2.4, 2.4)
    p.drawLine(10.0, 10.2, 10.0, 17.0)
    p.drawLine(14.0, 10.2, 14.0, 17.0)


def _draw_copy(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(8.0, 4.0, 11.5, 13.5), 2.4, 2.4)
    path = QPainterPath()
    path.moveTo(6.0, 7.0)
    path.lineTo(4.8, 7.0)
    path.quadTo(4.0, 7.0, 4.0, 7.8)
    path.lineTo(4.0, 19.2)
    path.quadTo(4.0, 20.0, 4.8, 20.0)
    path.lineTo(15.2, 20.0)
    path.quadTo(16.0, 20.0, 16.0, 19.2)
    path.lineTo(16.0, 18.2)
    p.drawPath(path)


def _draw_pencil(p: QPainter) -> None:
    path = QPainterPath()
    path.moveTo(4.0, 20.0)
    path.lineTo(5.2, 15.0)
    path.lineTo(15.2, 5.0)
    path.lineTo(19.0, 8.8)
    path.lineTo(9.0, 18.8)
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(13.2, 7.0, 17.0, 10.8)
    p.drawLine(5.2, 15.0, 9.0, 18.8)


def _draw_plus(p: QPainter) -> None:
    p.drawLine(12.0, 5.0, 12.0, 19.0)
    p.drawLine(5.0, 12.0, 19.0, 12.0)


def _draw_minus(p: QPainter) -> None:
    p.drawLine(6.5, 12.0, 17.5, 12.0)


def _draw_close(p: QPainter) -> None:
    p.drawLine(7.0, 7.0, 17.0, 17.0)
    p.drawLine(17.0, 7.0, 7.0, 17.0)


def _draw_check(p: QPainter) -> None:
    p.drawLine(4.8, 12.8, 9.6, 17.6)
    p.drawLine(9.6, 17.6, 19.2, 6.4)


def _draw_photo(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(3.0, 5.0, 18.0, 14.0), 3.0, 3.0)
    p.drawEllipse(QRectF(7.0, 8.2, 3.4, 3.4))
    path = QPainterPath()
    path.moveTo(4.4, 17.4)
    path.lineTo(9.8, 12.4)
    path.lineTo(13.2, 15.6)
    path.lineTo(15.8, 13.2)
    path.lineTo(20.0, 17.2)
    p.drawPath(path)


def _draw_chevron(p: QPainter) -> None:
    p.drawLine(5.4, 8.7, 12.0, 15.3)
    p.drawLine(12.0, 15.3, 18.6, 8.7)


def _draw_chart(p: QPainter) -> None:
    p.drawLine(4.0, 3.8, 4.0, 20.2)
    p.drawLine(4.0, 20.2, 20.6, 20.2)
    path = QPainterPath()
    path.moveTo(7.0, 15.8)
    path.lineTo(10.8, 11.2)
    path.lineTo(14.2, 13.6)
    path.lineTo(19.4, 6.8)
    p.drawPath(path)
    p.save()
    p.setBrush(p.pen().color())
    p.drawEllipse(QPointF(19.4, 6.8), 1.15, 1.15)
    p.restore()


def _draw_receipt(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(5.0, 3.0, 14.0, 18.0), 2.4, 2.4)
    p.drawLine(8.6, 8.0, 15.4, 8.0)
    p.drawLine(8.6, 12.0, 15.4, 12.0)
    p.drawLine(8.6, 16.0, 13.2, 16.0)


def _draw_maximize(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(5.4, 5.4, 13.2, 13.2), 1.6, 1.6)


def _draw_restore(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(4.4, 7.6, 11.2, 11.2), 1.6, 1.6)
    p.drawLine(7.6, 7.6, 7.6, 4.4)
    p.drawLine(7.6, 4.4, 18.8, 4.4)
    p.drawLine(18.8, 4.4, 18.8, 15.6)
    p.drawLine(18.8, 15.6, 15.6, 15.6)


def _draw_gear(p: QPainter) -> None:
    outline = QPainterPath()
    teeth = 8
    for index in range(teeth * 2):
        angle = math.radians(index * 360.0 / (teeth * 2) - 90.0)
        radius = 9.4 if index % 2 == 0 else 7.1
        point = QPointF(
            12.0 + radius * math.cos(angle),
            12.0 + radius * math.sin(angle),
        )
        if index == 0:
            outline.moveTo(point)
        else:
            outline.lineTo(point)
    outline.closeSubpath()

    p.drawPath(outline)
    p.drawEllipse(QRectF(9.2, 9.2, 5.6, 5.6))


def _lines(p: QPainter, *points: tuple[float, float]) -> None:
    path = QPainterPath(QPointF(*points[0]))
    for point in points[1:]:
        path.lineTo(QPointF(*point))
    p.drawPath(path)


def _draw_clock(p: QPainter) -> None:
    p.drawEllipse(QRectF(3, 3, 18, 18))
    _lines(p, (12, 6.5), (12, 12), (15.6, 14.5))


def _draw_car(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(3, 10, 18, 7.5), 2, 2)
    _lines(p, (5, 10), (7, 5.6), (17, 5.6), (19, 10))
    p.drawLine(5, 17.5, 5, 20)
    p.drawLine(19, 17.5, 19, 20)
    p.drawLine(6.5, 13.6, 8.3, 13.6)
    p.drawLine(15.7, 13.6, 17.5, 13.6)


def _draw_hanger(p: QPainter) -> None:
    path = QPainterPath(QPointF(9.5, 7.2))
    path.cubicTo(9.5, 3.5, 15.1, 3.9, 14.8, 7.1)
    path.cubicTo(14.5, 8.6, 12, 9, 12, 11)
    p.drawPath(path)
    _lines(p, (12, 11), (21, 17), (21, 19), (3, 19), (3, 17), (12, 11))


def _draw_box(p: QPainter) -> None:
    _lines(p, (12, 3), (20.5, 7.8), (20.5, 16.1), (12, 21), (3.5, 16.1), (3.5, 7.8), (12, 3))
    _lines(p, (3.5, 7.8), (12, 12.7), (20.5, 7.8))
    p.drawLine(12, 12.7, 12, 21)


def _draw_bars(p: QPainter) -> None:
    for left, top in ((3.5, 13), (10, 8.5), (16.5, 4)):
        p.drawRoundedRect(QRectF(left, top, 4, 20 - top), 0.7, 0.7)


def _draw_wallet(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(3.5, 7.3, 17, 12.8), 2, 2)
    _lines(p, (5, 7.3), (6.5, 4.5), (17, 4.5), (18.6, 7.3))
    p.drawRoundedRect(QRectF(15, 11.5, 5.5, 4.5), 1, 1)


def _draw_tag(p: QPainter) -> None:
    _lines(p, (3.5, 4.5), (11, 4.5), (21, 14.4), (14.3, 21), (3.5, 10.6), (3.5, 4.5))
    p.drawEllipse(QRectF(6.7, 7.4, 2, 2))


def _draw_exchange(p: QPainter) -> None:
    p.drawLine(3, 8, 20, 8)
    _lines(p, (16, 4), (20, 8), (16, 12))
    p.drawLine(21, 16, 4, 16)
    _lines(p, (8, 12), (4, 16), (8, 20))


def _draw_coins(p: QPainter) -> None:
    for top in (4, 10, 16):
        p.drawRoundedRect(QRectF(4.5, top, 15, 4), 2, 2)


def _draw_currency(p: QPainter) -> None:
    stroke = QPainterPath(QPointF(17.5, 6.7))
    stroke.cubicTo(14, 3.2, 5.7, 4.4, 6.5, 8.8)
    stroke.cubicTo(7.2, 12.1, 16.6, 11.1, 17.5, 15.2)
    stroke.cubicTo(18.6, 19.9, 9.7, 21.3, 5.7, 17.4)
    p.drawPath(stroke)
    p.drawLine(12, 2.7, 12, 21.3)


def _draw_grid(p: QPainter) -> None:
    for x, y in ((4, 4), (13, 4), (4, 13), (13, 13)):
        p.drawRoundedRect(QRectF(x, y, 6, 6), 1, 1)


def _draw_comment(p: QPainter) -> None:
    path = QPainterPath(QPointF(4, 4.5))
    path.lineTo(20, 4.5)
    path.quadTo(21.5, 4.5, 21.5, 6)
    path.lineTo(21.5, 15)
    path.quadTo(21.5, 16.5, 20, 16.5)
    path.lineTo(10, 16.5)
    path.lineTo(5.5, 20.5)
    path.lineTo(5.5, 16.5)
    path.quadTo(2.5, 16.5, 2.5, 15)
    path.lineTo(2.5, 6)
    path.quadTo(2.5, 4.5, 4, 4.5)
    p.drawPath(path)


def _draw_bolt(p: QPainter) -> None:
    _lines(p, (13.5, 2), (5.5, 13), (11.4, 13), (10.5, 22), (19, 10), (13, 10), (13.5, 2))


def _draw_filters(p: QPainter) -> None:
    for center, y in ((14.5, 6), (9, 12), (16, 18)):
        p.drawLine(3, y, center - 2, y)
        p.drawLine(center + 2, y, 21, y)
        p.drawEllipse(QRectF(center - 2, y - 2, 4, 4))


def _draw_bag(p: QPainter) -> None:
    p.drawRoundedRect(QRectF(4.5, 8, 15, 13), 2, 2)
    p.drawArc(QRectF(8, 3, 8, 10), 0, 180 * 16)


_DRAWERS = {
    "search": _draw_search,
    "calendar": _draw_calendar,
    "refresh": _draw_refresh,
    "trash": _draw_trash,
    "copy": _draw_copy,
    "pencil": _draw_pencil,
    "plus": _draw_plus,
    "minus": _draw_minus,
    "close": _draw_close,
    "check": _draw_check,
    "photo": _draw_photo,
    "chevron": _draw_chevron,
    "chart": _draw_chart,
    "receipt": _draw_receipt,
    "gear": _draw_gear,
    "maximize": _draw_maximize,
    "restore": _draw_restore,
    "clock": _draw_clock,
    "car": _draw_car,
    "hanger": _draw_hanger,
    "box": _draw_box,
    "bars": _draw_bars,
    "wallet": _draw_wallet,
    "tag": _draw_tag,
    "exchange": _draw_exchange,
    "coins": _draw_coins,
    "currency": _draw_currency,
    "grid": _draw_grid,
    "comment": _draw_comment,
    "bolt": _draw_bolt,
    "filters": _draw_filters,
    "bag": _draw_bag,
}


def icon_pixmap(name: str, color: str = DEFAULT_ICON_COLOR, canvas: int = ICON_CANVAS) -> QPixmap:
    pm = QPixmap(canvas, canvas)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    scale = canvas / 24.0
    p.scale(scale, scale)
    pen = QPen(QColor(color))
    pen.setWidthF(1.75)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    _DRAWERS[name](p)
    p.end()
    return pm


def icon(name: str, color: str = DEFAULT_ICON_COLOR) -> QIcon:
    return QIcon(icon_pixmap(name, color))


# ------------------------------------------------------------------------------- logo
def logo_image(size: int) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    rect = QRectF(0.6, 0.6, size - 1.2, size - 1.2)
    radius = size * 0.26
    background = QLinearGradient(0, 0, size, size)
    background.setColorAt(0, QColor("#3E1C5C"))
    background.setColorAt(0.52, QColor("#160B27"))
    background.setColorAt(1, QColor("#0E0719"))
    p.setBrush(background)
    p.setPen(QPen(QColor("#563573"), max(1.0, size * 0.012)))
    p.drawRoundedRect(rect, radius, radius)

    font = QFont("Segoe UI")
    font.setPixelSize(max(7, int(size * 0.77)))
    font.setWeight(QFont.Weight.Black)
    font.setItalic(True)
    p.setFont(font)
    lettering = QLinearGradient(0, 0, 0, size)
    lettering.setColorAt(0.2, QColor("#FFF6FF"))
    lettering.setColorAt(0.79, QColor("#BC76F4"))
    p.setPen(QPen(lettering, 1))
    p.drawText(img.rect(), Qt.AlignmentFlag.AlignCenter, "G")
    p.end()
    return img


def logo_pixmap(size: int = 26) -> QPixmap:
    pm = QPixmap.fromImage(logo_image(size * 2))
    pm.setDevicePixelRatio(2.0)
    return pm


def brand_image(size: int) -> QImage:
    """Application icon artwork, falling back to the drawn «G» placeholder."""
    image = QImage(str(resource_path(*BRAND_ICON)))
    if not image.isNull():
        return image.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    return logo_image(size)


def app_icon() -> QIcon:
    result = QIcon()
    for size in (16, 20, 24, 32, 40, 48, 64, 96, 128, 256):
        result.addPixmap(QPixmap.fromImage(brand_image(size)))
    return result


def _ico_dib(image: QImage) -> bytes:
    """32-bit BMP payload for an .ico entry (Explorer reads alpha reliably)."""
    size = image.width()
    image = image.convertToFormat(QImage.Format.Format_ARGB32)
    data = bytes(image.constBits())
    stride = image.bytesPerLine()

    header = struct.pack(
        "<IiiHHIIiiII",
        40,
        size,
        size * 2,
        1,
        32,
        0,
        size * size * 4,
        0,
        0,
        0,
        0,
    )
    xor_rows = bytearray()
    for y in range(size - 1, -1, -1):
        start = y * stride
        xor_rows += data[start : start + size * 4]

    mask_stride = ((size + 31) // 32) * 4
    mask = bytearray(mask_stride * size)
    for y in range(size):
        start = y * stride
        row = (size - 1 - y) * mask_stride
        for x in range(size):
            if data[start + x * 4 + 3] == 0:
                mask[row + (x >> 3)] |= 0x80 >> (x & 7)
    return header + bytes(xor_rows) + bytes(mask)


def write_ico(
    path: str | Path, sizes: tuple[int, ...] = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)
) -> Path:
    """Write a multi-size Windows .ico: BMP entries, PNG only for 256."""
    payloads: list[tuple[int, bytes]] = []
    for size in sizes:
        image = brand_image(size)
        if size >= 256:
            data = QByteArray()
            buffer = QBuffer(data)
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            image.save(buffer, "PNG")
            buffer.close()
            payloads.append((size, bytes(data)))
        else:
            payloads.append((size, _ico_dib(image)))

    header = struct.pack("<HHH", 0, 1, len(payloads))
    offset = 6 + 16 * len(payloads)
    entries = bytearray()
    blobs = bytearray()
    for size, payload in payloads:
        entries += struct.pack(
            "<BBBBHHII",
            size if size < 256 else 0,
            size if size < 256 else 0,
            0,
            0,
            1,
            32,
            len(payload),
            offset,
        )
        offset += len(payload)
        blobs += payload

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(header + bytes(entries) + bytes(blobs))
    return target


# ------------------------------------------------------------------------ QSS assets
def ensure_ui_assets() -> dict[str, str]:
    ui_dir = data_dir() / "ui"
    ui_dir.mkdir(parents=True, exist_ok=True)
    chevron = ui_dir / "chevron_down.png"
    if not chevron.exists():
        icon_pixmap("chevron", "#9AA0A8", 48).save(str(chevron), "PNG")
    return {"chevron": chevron.as_posix()}
