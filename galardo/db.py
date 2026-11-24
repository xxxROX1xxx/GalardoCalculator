from __future__ import annotations

import sqlite3
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from .legacy import LegacyDeal, legacy_history_path, load_legacy_deals
from .paths import data_dir

LEGACY_IMPORT_FLAG = "legacy_import_done"
LEGACY_PAIRS_FLAG = "legacy_pairs_backfilled"

SCHEMA = """
CREATE TABLE IF NOT EXISTS deals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product     TEXT    NOT NULL,
    side        TEXT    NOT NULL CHECK (side IN ('buy', 'sell')),
    amount      REAL    NOT NULL,
    quantity    REAL    NOT NULL DEFAULT 1,
    parent_id   INTEGER,
    sort_key    REAL    NOT NULL DEFAULT 0,
    dealt_at    TEXT    NOT NULL,
    comment     TEXT    NOT NULL DEFAULT '',
    photo       BLOB,
    created_at  TEXT    NOT NULL,
    category    TEXT    NOT NULL DEFAULT 'transport',
    legacy_id   TEXT
);
CREATE INDEX IF NOT EXISTS idx_deals_dealt_at ON deals (dealt_at DESC);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

CATEGORIES: dict[str, str] = {
    "transport": "Транспорт",
    "clothing": "Одежда",
    "items": "Предметы",
}


@dataclass(slots=True)
class Deal:
    id: int
    product: str
    side: str
    amount: float
    dealt_at: str
    comment: str
    photo: bytes | None
    created_at: str
    category: str = "transport"
    quantity: float = 1.0
    parent_id: int | None = None
    sort_key: float = 0.0

    @property
    def signed_amount(self) -> float:
        return -self.amount if self.side == "buy" else self.amount


@dataclass(slots=True)
class DayStat:
    """Sales of one item during one day."""

    day: date
    count: int
    total: float
    median: float


@dataclass(slots=True)
class ProductStats:
    """Median / min / max prices and per-day sales for a single item."""

    product: str
    side: str
    start: date
    end: date
    days: list[DayStat]
    count: int
    total: float
    median: float | None
    average: float | None
    minimum: float | None
    maximum: float | None


def parse_deal_moment(value: str) -> datetime | None:
    """Read both ISO timestamps and the old 'dd.mm.yyyy HH:MM' style."""
    text = (value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        parsed = None
    if parsed is not None and parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    if parsed is not None:
        return parsed
    for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


class Database:
    """SQLite storage. The file lives in %APPDATA%/Galardo, so history
    survives closing the program, reinstalling and rebuilding the exe."""

    def __init__(
        self,
        path: str | Path | None = None,
        legacy_source: str | Path | None = None,
    ) -> None:
        self.legacy_imported = 0
        if path is None:
            self.path: Path | None = data_dir() / "galardo.db"
            target = str(self.path)
        elif str(path) == ":memory:":
            self.path = None
            target = ":memory:"
        else:
            self.path = Path(path)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            target = str(self.path)

        self._conn = sqlite3.connect(target)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._ensure_columns()
        self._conn.commit()

        # The real app database (path is None) picks up history from the old
        # "Calculating" version automatically.  Tests and previews use an
        # explicit path, so they never touch the user's real data.
        if path is None or legacy_source is not None:
            self._auto_import_legacy(legacy_source)
        self._migrate_legacy_pairs()

    def _ensure_columns(self) -> None:
        """Add columns introduced in newer versions without losing history."""
        columns = {
            str(row["name"])
            for row in self._conn.execute("PRAGMA table_info(deals)")
        }
        if "category" not in columns:
            self._conn.execute(
                """ALTER TABLE deals
                   ADD COLUMN category TEXT NOT NULL DEFAULT 'transport'"""
            )
        if "legacy_id" not in columns:
            self._conn.execute("ALTER TABLE deals ADD COLUMN legacy_id TEXT")
        if "quantity" not in columns:
            self._conn.execute(
                "ALTER TABLE deals ADD COLUMN quantity REAL NOT NULL DEFAULT 1"
            )
        if "parent_id" not in columns:
            self._conn.execute("ALTER TABLE deals ADD COLUMN parent_id INTEGER")
        if "sort_key" not in columns:
            self._conn.execute("ALTER TABLE deals ADD COLUMN sort_key REAL")
            self._renumber_sort_keys()
        self._conn.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS idx_deals_legacy_id
               ON deals (legacy_id)"""
        )

    def _renumber_sort_keys(self) -> None:
        """Разложить существующие сделки по текущему порядку дат.

        Вызывается только при первом появлении колонки sort_key и после
        импорта старой истории — дальше порядок задаёт пользователь.
        """
        rows = self._conn.execute(
            "SELECT id FROM deals ORDER BY dealt_at DESC, id DESC"
        ).fetchall()
        self._conn.executemany(
            "UPDATE deals SET sort_key = ? WHERE id = ?",
            [(float(index), int(row["id"])) for index, row in enumerate(rows)],
        )
        self._conn.commit()

    # ---------------------------------------------------------- legacy import
    def _migrate_legacy_pairs(self) -> None:
        if self.get_setting(LEGACY_PAIRS_FLAG, "0") == "1":
            return
        with self._conn:
            first_run = self._conn.execute(
                """INSERT INTO settings (key, value) VALUES (?, '1')
                   ON CONFLICT(key) DO UPDATE SET value = excluded.value
                   WHERE settings.value != excluded.value""",
                (LEGACY_PAIRS_FLAG,),
            ).rowcount
            if first_run:
                self._link_unambiguous_pairs()

    def _link_unambiguous_pairs(self, *, imported_only: bool = False) -> None:
        rows = self._conn.execute(
            """SELECT id, product, side, quantity, category, dealt_at, parent_id, legacy_id
               FROM deals"""
        ).fetchall()
        linked_buys = {row["parent_id"] for row in rows if row["side"] == "sell"}
        groups: dict[tuple[str, str, float], list[tuple[datetime, int, str]]] = (
            defaultdict(list)
        )
        for row in rows:
            if row["parent_id"] is not None or row["id"] in linked_buys:
                continue
            if imported_only and row["legacy_id"] is None:
                continue
            product = " ".join(row["product"].casefold().split())
            moment = parse_deal_moment(row["dealt_at"])
            if product and product != "без названия" and moment is not None:
                key = (product, row["category"], row["quantity"])
                groups[key].append((moment, row["id"], row["side"]))

        pairs: list[tuple[int, int]] = []
        for events in groups.values():
            # Сопоставляем одиночные циклы покупки и продажи. Несколько
            # открытых покупок или лишняя продажа делают цикл неоднозначным.
            cycle: list[int] = []
            open_buys = 0
            for _, deal_id, side in sorted(events):
                if side == "buy":
                    if open_buys == 0:
                        if len(cycle) == 2:
                            pairs.append((cycle[0], cycle[1]))
                        cycle.clear()
                    open_buys += 1
                elif cycle:
                    open_buys = max(0, open_buys - 1)
                else:
                    continue
                cycle.append(deal_id)
            if open_buys == 0 and len(cycle) == 2:
                pairs.append((cycle[0], cycle[1]))

        self._conn.executemany(
            "UPDATE deals SET parent_id = ? WHERE id = ? AND parent_id IS NULL",
            pairs,
        )

    def _auto_import_legacy(
        self, source: str | Path | None = None
    ) -> None:
        """One-time migration from the old "Calculating" version.

        Imported rows remember their old id, so even if an existing Galardo
        database is not empty the migration adds only missing transactions
        and never duplicates them.
        """
        if self.get_setting(LEGACY_IMPORT_FLAG, "0") == "1":
            return
        path = Path(source) if source is not None else legacy_history_path()
        if path is None or not path.is_file():
            return
        if self.import_legacy(path):
            self.set_setting(LEGACY_IMPORT_FLAG, "1")

    def import_legacy(self, source: str | Path) -> int:
        """Copy deals from an old ``transactions.json`` file."""
        deals: list[LegacyDeal] = load_legacy_deals(source)
        if not deals:
            return 0
        existing = {
            (
                str(row["product"]),
                str(row["side"]),
                round(float(row["amount"]), 2),
                str(row["dealt_at"]),
                str(row["comment"]),
            )
            for row in self._conn.execute(
                "SELECT product, side, amount, dealt_at, comment FROM deals"
            )
        }
        rows = []
        for deal in deals:
            key = (
                deal.product,
                deal.side,
                round(deal.amount, 2),
                deal.dealt_at,
                deal.comment,
            )
            if key in existing:
                continue
            existing.add(key)
            rows.append(deal)
        if not rows:
            return 0
        table_columns = {
            str(row["name"])
            for row in self._conn.execute("PRAGMA table_info(deals)")
        }
        names = [
            "product",
            "side",
            "amount",
            "dealt_at",
            "comment",
            "photo",
            "created_at",
            "category",
            "legacy_id",
        ]
        if "viewed_at" in table_columns:  # very old databases
            names.insert(4, "viewed_at")
        with self._conn:
            inserted = self._conn.executemany(
                f"""INSERT OR IGNORE INTO deals ({", ".join(names)})
                    VALUES ({", ".join("?" for _ in names)})""",
                [
                    tuple(
                        {
                            "product": deal.product,
                            "side": deal.side,
                            "amount": deal.amount,
                            "viewed_at": "",
                            "dealt_at": deal.dealt_at,
                            "comment": deal.comment,
                            "photo": deal.photo,
                            "created_at": deal.created_at,
                            "category": "transport",
                            "legacy_id": deal.legacy_id,
                        }[name]
                        for name in names
                    )
                    for deal in rows
                ],
            ).rowcount
            if inserted and self.get_setting(LEGACY_PAIRS_FLAG, "0") == "1":
                self._link_unambiguous_pairs(imported_only=True)
        self.legacy_imported += inserted
        if inserted:
            self._renumber_sort_keys()
        return inserted

    # ------------------------------------------------------------------ deals
    def add_deal(
        self,
        *,
        product: str,
        side: str,
        amount: float,
        dealt_at: str,
        comment: str,
        photo: bytes | None,
        created_at: str,
        category: str = "transport",
        quantity: float = 1.0,
        parent_id: int | None = None,
    ) -> int:
        sort_key = self._next_sort_key()
        cur = self._conn.execute(
            """INSERT INTO deals
               (product, side, amount, quantity, parent_id, sort_key,
                dealt_at, comment, photo, created_at, category)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                product,
                side,
                amount,
                max(1.0, float(quantity)),
                parent_id,
                sort_key,
                dealt_at,
                comment,
                photo,
                created_at,
                category,
            ),
        )
        # новая продажа «такого же» товара поднимает всю пару наверх
        if parent_id is not None:
            self._conn.execute(
                "UPDATE deals SET sort_key = ? WHERE id = ?",
                (sort_key, parent_id),
            )
        self._conn.commit()
        return int(cur.lastrowid)

    def _next_sort_key(self) -> float:
        row = self._conn.execute(
            "SELECT MIN(sort_key) AS first FROM deals"
        ).fetchone()
        first = row["first"] if row is not None else None
        return (float(first) - 1.0) if first is not None else 0.0

    def update_deal(
        self,
        deal_id: int,
        *,
        product: str,
        side: str,
        amount: float,
        dealt_at: str,
        comment: str,
        photo: bytes | None,
        category: str = "transport",
        quantity: float | None = None,
    ) -> None:
        self._conn.execute(
            """UPDATE deals
               SET product = ?, side = ?, amount = ?, dealt_at = ?,
                   comment = ?, photo = ?, category = ?,
                   quantity = COALESCE(?, quantity)
               WHERE id = ?""",
            (
                product,
                side,
                amount,
                dealt_at,
                comment,
                photo,
                category,
                None if quantity is None else max(1.0, float(quantity)),
                deal_id,
            ),
        )
        if side == "buy":
            # покупка не может быть чьей-то продажей
            self._conn.execute(
                "UPDATE deals SET parent_id = NULL WHERE id = ?", (deal_id,)
            )
        else:
            # если покупку переделали в продажу, её «дети» становятся сами по себе
            self._conn.execute(
                "UPDATE deals SET parent_id = NULL WHERE parent_id = ?",
                (deal_id,),
            )
        self._conn.commit()

    def delete_deal(self, deal_id: int) -> None:
        self._conn.execute(
            "UPDATE deals SET parent_id = NULL WHERE parent_id = ?", (deal_id,)
        )
        self._conn.execute("DELETE FROM deals WHERE id = ?", (deal_id,))
        self._conn.commit()

    def set_sort_keys(self, keys: dict[int, float]) -> None:
        if not keys:
            return
        self._conn.executemany(
            "UPDATE deals SET sort_key = ? WHERE id = ?",
            [(float(value), int(deal_id)) for deal_id, value in keys.items()],
        )
        self._conn.commit()

    def set_deal_photo(self, deal_id: int, photo: bytes | None) -> None:
        self._conn.execute(
            "UPDATE deals SET photo = ? WHERE id = ?", (photo, deal_id)
        )
        self._conn.commit()

    def linked_sales(self, deal_id: int) -> int:
        """Сколько продаж уже привязано к этой покупке."""
        row = self._conn.execute(
            "SELECT COUNT(*) AS count FROM deals WHERE parent_id = ?",
            (deal_id,),
        ).fetchone()
        return int((row["count"] if row is not None else 0) or 0)

    def get_deal(self, deal_id: int) -> Deal | None:
        row = self._conn.execute(
            "SELECT * FROM deals WHERE id = ?", (deal_id,)
        ).fetchone()
        return self._row_to_deal(row) if row else None

    def all_deals(
        self, query: str = "", category: str | None = None
    ) -> list[Deal]:
        sql = "SELECT * FROM deals"
        params: tuple[str, ...] = ()
        if category:
            sql += " WHERE category = ?"
            params = (category,)
        sql += " ORDER BY sort_key ASC, dealt_at DESC, id DESC"
        rows = self._conn.execute(sql, params).fetchall()
        deals = [self._row_to_deal(row) for row in rows]
        if query:
            needle = query.casefold()
            deals = [
                deal
                for deal in deals
                if needle in deal.product.casefold()
                or needle in deal.comment.casefold()
            ]
        return deals

    def first_dealt_at(self) -> str | None:
        """Earliest deal date — the anchor for weekly groups."""
        row = self._conn.execute(
            "SELECT MIN(dealt_at) AS first FROM deals"
        ).fetchone()
        return str(row["first"]) if row and row["first"] else None

    # -------------------------------------------------------------- statistics
    def position_counts(self) -> tuple[int, int]:
        """Closed buy+sell positions and active (bought, not sold) positions.

        A closed position is a purchase with at least one explicitly linked
        sale. A purchase without linked sales is still in stock. Standalone
        sale rows are not counted as positions.
        """
        rows = self._conn.execute(
            "SELECT id, side, parent_id FROM deals"
        ).fetchall()
        buys = {row["id"] for row in rows if row["side"] == "buy"}
        sold = {
            row["parent_id"]
            for row in rows
            if row["side"] == "sell"
            and row["parent_id"] is not None
            and row["parent_id"] in buys
        }
        return len(sold), len(buys - sold)

    def product_names(self, category: str | None = None) -> list[str]:
        """Unique item names, most recently traded first."""
        sql = "SELECT product, MAX(dealt_at) AS last_at FROM deals"
        params: tuple[str, ...] = ()
        if category:
            sql += " WHERE category = ?"
            params = (category,)
        sql += " GROUP BY product COLLATE NOCASE ORDER BY last_at DESC"
        rows = self._conn.execute(sql, params).fetchall()
        names: list[str] = []
        seen: set[str] = set()
        for row in rows:
            name = str(row["product"]).strip()
            key = name.casefold()
            if not name or key in seen:
                continue
            seen.add(key)
            names.append(name)
        return names

    def product_stats(
        self,
        product: str,
        side: str = "sell",
        days: int = 30,
        category: str | None = None,
        today: date | None = None,
    ) -> ProductStats:
        """Aggregate one item over the last ``days`` calendar days.

        The item name is matched case-insensitively; only its own deals are
        counted, so another player's purchases never mix into the median.
        """
        window = max(1, int(days))
        end = today or date.today()
        start = end - timedelta(days=window - 1)
        needle = (product or "").strip().casefold()

        buckets: dict[date, list[float]] = {}
        if needle:
            rows = self._conn.execute(
                "SELECT product, amount, dealt_at, category FROM deals"
                " WHERE side = ?",
                (side,),
            ).fetchall()
            for row in rows:
                if category and str(row["category"]) != category:
                    continue
                if str(row["product"]).strip().casefold() != needle:
                    continue
                moment = parse_deal_moment(str(row["dealt_at"]))
                if moment is None:
                    continue
                day = moment.date()
                if start <= day <= end:
                    buckets.setdefault(day, []).append(float(row["amount"]))

        day_stats = [
            DayStat(
                day=day,
                count=len(values),
                total=sum(values),
                median=float(statistics.median(values)),
            )
            for day, values in sorted(buckets.items())
        ]
        amounts = [value for values in buckets.values() for value in values]
        return ProductStats(
            product=product.strip(),
            side=side,
            start=start,
            end=end,
            days=day_stats,
            count=len(amounts),
            total=sum(amounts),
            median=float(statistics.median(amounts)) if amounts else None,
            average=(sum(amounts) / len(amounts)) if amounts else None,
            minimum=min(amounts) if amounts else None,
            maximum=max(amounts) if amounts else None,
        )

    def market_own_stats(
        self,
        product: str,
        category: str,
        days: int = 30,
        today: date | None = None,
        *,
        aliases: tuple[str, ...] = (),
    ) -> tuple[int, float | None, int, float | None]:
        """Мои покупки и продажи одного предмета маркета за окно дней.

        Сумма сделки в журнале — это цена × количество, поэтому средняя
        считается за единицу: сумма / количество.
        """
        window = max(1, int(days))
        end = today or date.today()
        start = end - timedelta(days=window - 1)
        names = {name.strip().casefold() for name in (product, *aliases) if name and name.strip()}
        if not names:
            return 0, None, 0, None

        totals: dict[str, list[float]] = {
            "buy": [0.0, 0.0, 0.0],
            "sell": [0.0, 0.0, 0.0],
        }
        rows = self._conn.execute(
            "SELECT product, side, amount, quantity, dealt_at FROM deals"
            " WHERE category = ?",
            (category,),
        ).fetchall()
        for row in rows:
            if str(row["product"]).strip().casefold() not in names:
                continue
            moment = parse_deal_moment(str(row["dealt_at"]))
            if moment is None or not (start <= moment.date() <= end):
                continue
            bucket = totals.get(str(row["side"]))
            if bucket is None:
                continue
            bucket[0] += 1
            bucket[1] += float(row["amount"])
            bucket[2] += float(row["quantity"] or 1.0)

        buy = totals["buy"]
        sell = totals["sell"]
        return (
            int(buy[0]),
            (buy[1] / buy[2]) if buy[2] else None,
            int(sell[0]),
            (sell[1] / sell[2]) if sell[2] else None,
        )

    # --------------------------------------------------------------- settings
    def get_setting(self, key: str, default: str) -> str:
        row = self._conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return str(row["value"]) if row else default

    def set_setting(self, key: str, value: str) -> None:
        self._conn.execute(
            """INSERT INTO settings (key, value) VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value""",
            (key, value),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    @staticmethod
    def _row_to_deal(row: sqlite3.Row) -> Deal:
        return Deal(
            id=int(row["id"]),
            product=str(row["product"]),
            side=str(row["side"]),
            amount=float(row["amount"]),
            dealt_at=str(row["dealt_at"]),
            comment=str(row["comment"]),
            photo=bytes(row["photo"]) if row["photo"] is not None else None,
            created_at=str(row["created_at"]),
            category=str(row["category"]),
            quantity=float(row["quantity"] or 1.0),
            parent_id=(
                int(row["parent_id"]) if row["parent_id"] is not None else None
            ),
            sort_key=float(row["sort_key"] or 0.0),
        )
