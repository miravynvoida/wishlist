import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = os.getenv("DATABASE_PATH", "/app/data/wishlist.sqlite3")

def _connect():
    path = Path(DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

@contextmanager
def connection():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db(owner_ids):
    with connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS owners (
            telegram_id INTEGER PRIMARY KEY,
            display_name TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL REFERENCES owners(telegram_id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            emoji TEXT NOT NULL DEFAULT '🎁',
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(owner_id, name)
        );
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL REFERENCES owners(telegram_id) ON DELETE CASCADE,
            category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            url TEXT NOT NULL DEFAULT '',
            price TEXT NOT NULL DEFAULT '',
            image_url TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL UNIQUE REFERENCES items(id) ON DELETE CASCADE,
            reserver_id INTEGER NOT NULL,
            reserved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_items_owner ON items(owner_id);
        CREATE INDEX IF NOT EXISTS idx_items_category ON items(category_id);
        """)
        defaults = [
            ("🧢", "Аксессуары"), ("👕", "Одежда"), ("🍜", "Еда и напитки"),
            ("🎮", "Техника и игры"), ("📚", "Книги"), ("🏠", "Для дома"),
            ("🎟️", "Впечатления"), ("✨", "Другое")
        ]
        for i, owner_id in enumerate(owner_ids):
            display = "Владелец 1" if i == 0 else "Владелец 2"
            conn.execute(
                "INSERT OR IGNORE INTO owners(telegram_id, display_name) VALUES(?, ?)",
                (owner_id, display)
            )
            for order, (emoji, name) in enumerate(defaults):
                conn.execute(
                    "INSERT OR IGNORE INTO categories(owner_id,name,emoji,sort_order) VALUES(?,?,?,?)",
                    (owner_id, name, emoji, order)
                )

def row_dict(row):
    return dict(row) if row else None
