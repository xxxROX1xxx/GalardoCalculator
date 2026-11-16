"""Import history from the old "Calculating" version.

The old .NET/Avalonia build kept everything in a single JSON file:
``%APPDATA%\\Calculating\\transactions.json``.  Photos are stored there as
``data:image/...;base64,...`` strings, so no extra files are needed.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

LEGACY_DIR_NAME = "Calculating"
LEGACY_FILE_NAME = "transactions.json"


@dataclass(slots=True, frozen=True)
class LegacyDeal:
    legacy_id: str
    product: str
    side: str
    amount: float
    dealt_at: str
    comment: str
    photo: bytes | None
    created_at: str


def legacy_history_path() -> Path | None:
    """Path to the old app's JSON history, if it exists on this machine."""
    bases: list[Path] = []
    for variable in ("APPDATA", "LOCALAPPDATA"):
        value = os.environ.get(variable)
        if value:
            bases.append(Path(value))
    bases.append(Path.home() / "AppData" / "Roaming")
    seen: set[Path] = set()
    for base in bases:
        candidate = base / LEGACY_DIR_NAME / LEGACY_FILE_NAME
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.is_file():
            return candidate
    return None


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _iso_local(value: object, fallback: str) -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return fallback
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed.strftime("%Y-%m-%dT%H:%M:%S")


def _decode_photo(value: object) -> bytes | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.startswith("data:"):
        _, _, text = text.partition(",")
    text = "".join(text.split())
    if not text:
        return None
    text += "=" * (-len(text) % 4)
    try:
        data = base64.b64decode(text, validate=False)
    except (ValueError, binascii.Error):
        return None
    return data or None


def _is_income(record: dict) -> bool:
    raw_type = record.get("Type")
    if raw_type is not None:
        try:
            return int(raw_type) == 1
        except (TypeError, ValueError):
            pass
    return bool(record.get("IsIncome"))


def _legacy_key(record: dict, *parts: str) -> str:
    """Stable id from the old app, or a content hash for id-less records."""
    raw_id = str(record.get("Id") or "").strip()
    if raw_id:
        return raw_id
    digest = hashlib.sha1("\x1f".join(parts).encode("utf-8")).hexdigest()
    return f"content:{digest}"


def load_legacy_deals(source: str | Path) -> list[LegacyDeal]:
    """Read the old JSON file.  Bad records are skipped, never fatal."""
    try:
        raw = Path(source).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    if isinstance(data, dict):
        data = (
            data.get("Transactions")
            or data.get("transactions")
            or data.get("Items")
            or []
        )
    if not isinstance(data, list):
        return []

    deals: list[LegacyDeal] = []
    for record in data:
        if not isinstance(record, dict):
            continue
        product = str(record.get("ProductName") or "").strip()
        if not product:
            product = "Без названия"
        try:
            amount = abs(float(record.get("Amount") or 0))
        except (TypeError, ValueError):
            continue

        now = _now_iso()
        dealt_at = _iso_local(record.get("DateTime"), now)
        created_at = _iso_local(record.get("CreatedAt"), dealt_at)
        side = "sell" if _is_income(record) else "buy"
        comment = str(record.get("Comment") or "").strip()
        deals.append(
            LegacyDeal(
                legacy_id=_legacy_key(
                    record,
                    product,
                    side,
                    f"{amount:.6f}",
                    dealt_at,
                    comment,
                ),
                product=product,
                side=side,
                amount=amount,
                dealt_at=dealt_at,
                comment=comment,
                photo=_decode_photo(record.get("ImageData")),
                created_at=created_at,
            )
        )
    return deals
