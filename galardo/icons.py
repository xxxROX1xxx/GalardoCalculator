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

    hole = QPainterPath()
    hole.addEllipse(QRectF(9.2, 9.2, 5.6, 5.6))

    p.save()
    p.setBrush(p.pen().color())
    p.drawPath(outline.subtracted(hole))
    p.restore()


_DRAWERS = {
    "search": _draw_search,
    "calendar": _draw_calendar,
    "refresh": _draw_refresh,
    "trash": _draw_trash,
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
    p.setBrush(QColor("#0A0C0F"))
    p.setPen(QPen(QColor(255, 255, 255, 38), max(1.0, size * 0.012)))
    p.drawRoundedRect(rect, radius, radius)

    font = QFont("Segoe UI")
    font.setPixelSize(max(7, int(size * 0.56)))
    font.setWeight(QFont.Weight.Bold)
    p.setFont(font)
    p.setPen(QColor("#F5F6F8"))
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
