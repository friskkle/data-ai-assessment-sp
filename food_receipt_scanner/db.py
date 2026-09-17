import re
import sqlite3
from datetime import date, datetime, timedelta

from . import config

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store TEXT,
                date TEXT,
                total REAL,
                raw_text TEXT,
                image_path TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_id INTEGER NOT NULL,
                name TEXT,
                price REAL,
                quantity REAL DEFAULT 1,
                FOREIGN KEY (receipt_id) REFERENCES receipts (id)
            );
            """
        )


def insert_receipt(store, date, total, items, raw_text, image_path):
    """Store a parsed receipt and its line items. Returns the new receipt id."""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO receipts (store, date, total, raw_text, image_path, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (store, date, total, raw_text, image_path, datetime.now().isoformat()),
        )
        receipt_id = cur.lastrowid
        for item in items:
            conn.execute(
                "INSERT INTO items (receipt_id, name, price, quantity) VALUES (?, ?, ?, ?)",
                (receipt_id, item.get("name"), item.get("price"), item.get("quantity", 1)),
            )
    return receipt_id


def _parse_date(text):
    """Normalize a date the agent gives us to ISO YYYY-MM-DD.

    Tolerates what the model may actually send: "today", "yesterday", ISO,
    "20 June", "20 June 2026", "June 20 2026", "20/06/2026", etc.
    """
    text = str(text).strip().lower()
    today = date.today()
    if text == "today":
        return today.isoformat()
    if text == "yesterday":
        return (today - timedelta(days=1)).isoformat()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        return text

    # 20 June 2026 / 20 June  (missing year defaults to the current year)
    m = re.search(r"\b(\d{1,2})\s+([a-z]{3,9})[.,]?\s+(\d{4})\b", text)
    if not m:
        m = re.search(r"\b(\d{1,2})\s+([a-z]{3,9})[.,]?\b", text)
    if m:
        d, mo = int(m.group(1)), m.group(2)[:3]
        y = int(m.group(3)) if m.lastindex == 3 else today.year
        if mo in _MONTHS and 1 <= d <= 31:
            return f"{y:04d}-{_MONTHS[mo]:02d}-{d:02d}"

    # June 20 2026 / June 20
    m = re.search(r"\b([a-z]{3,9})[.,]?\s+(\d{1,2})[.,]?\s+(\d{4})\b", text)
    if not m:
        m = re.search(r"\b([a-z]{3,9})[.,]?\s+(\d{1,2})[.,]?\b", text)
    if m:
        mo, d = m.group(1)[:3], int(m.group(2))
        y = int(m.group(3)) if m.lastindex == 3 else today.year
        if mo in _MONTHS and 1 <= d <= 31:
            return f"{y:04d}-{_MONTHS[mo]:02d}-{d:02d}"

    # 20/06/2026, 20-06-2026, 20.06.2026
    m = re.search(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b", text)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{mo:02d}-{d:02d}"

    return text


def items_on_date(day):
    """All line items bought on a given date."""
    day = _parse_date(day)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT i.name, i.price, r.store FROM items i"
            " JOIN receipts r ON i.receipt_id = r.id"
            " WHERE r.date = ? ORDER BY i.name",
            (day,),
        ).fetchall()
    return [dict(r) for r in rows]


def total_spend_on_date(day):
    """Total money spent on a given date, plus the number of items."""
    day = _parse_date(day)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(i.price), 0) AS total, COUNT(*) AS item_count"
            " FROM items i JOIN receipts r ON i.receipt_id = r.id"
            " WHERE r.date = ?",
            (day,),
        ).fetchone()
    return {"total": round(row["total"], 2), "item_count": row["item_count"]}


def find_item_in_range(item_name, days):
    """Where (and when) a food item was bought in the last N days."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT i.name, i.price, r.store, r.date FROM items i"
            " JOIN receipts r ON i.receipt_id = r.id"
            " WHERE i.name LIKE ? AND r.date >= ? ORDER BY r.date DESC",
            (f"%{item_name}%", cutoff),
        ).fetchall()
    return [dict(r) for r in rows]


def recent_receipts(limit=20):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, store, date, total, image_path FROM receipts"
            " ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
