"""
AKIRA Database Module (db.py)
SQLite database manager providing full CRUD operations for search history and bookmarks.
"""

import os
import sqlite3
import json
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "akira.db")


def get_db_connection(db_path=None):
    """Create and return a new SQLite database connection."""
    target_path = db_path or DB_PATH
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=None):
    """Initialize database tables and indexes."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        # Search history table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                mode TEXT DEFAULT 'standard',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_history_created_at
            ON history(created_at DESC)
            """
        )

        # Bookmarks table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                summary TEXT NOT NULL,
                url TEXT,
                takeaways TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_bookmarks_created_at
            ON bookmarks(created_at DESC)
            """
        )
        conn.commit()
    finally:
        conn.close()


def add_search(query: str, mode: str = "standard", db_path=None) -> int:
    """Record a search query in history."""
    clean_query = query.strip()
    if not clean_query:
        return -1

    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO history (query, mode, created_at) VALUES (?, ?, ?)",
            (clean_query, mode, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_history(limit: int = 25, db_path=None) -> list:
    """Retrieve recent search queries ordered by timestamp descending."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, query, mode, created_at FROM history ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def clear_history(db_path=None) -> bool:
    """Remove all records from search history."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM history")
        conn.commit()
        return True
    finally:
        conn.close()


def delete_history_item(item_id: int, db_path=None) -> bool:
    """Delete a single history entry by id."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM history WHERE id = ?", (item_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def add_bookmark(title: str, summary: str, url: str = "", takeaways=None, db_path=None) -> int:
    """Save an article bookmark (replaces if already exists for same title)."""
    clean_title = title.strip()
    if not clean_title:
        return -1

    serialized_takeaways = json.dumps(takeaways) if isinstance(takeaways, (list, dict)) else (takeaways or "")

    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO bookmarks (title, summary, url, takeaways, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(title) DO UPDATE SET
                summary = excluded.summary,
                url = excluded.url,
                takeaways = excluded.takeaways,
                created_at = excluded.created_at
            """,
            (clean_title, summary.strip(), url.strip(), serialized_takeaways, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        bookmark_id = cursor.lastrowid
        if not bookmark_id or bookmark_id == 0:
            cursor.execute("SELECT id FROM bookmarks WHERE title = ? COLLATE NOCASE", (clean_title,))
            row = cursor.fetchone()
            if row:
                bookmark_id = row[0]
        return bookmark_id or 1
    finally:
        conn.close()


def get_bookmarks(db_path=None) -> list:
    """Retrieve all bookmarked articles ordered by creation date."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, summary, url, takeaways, created_at FROM bookmarks ORDER BY id DESC"
        )
        rows = cursor.fetchall()
        result = []
        for row in rows:
            item = dict(row)
            if item.get("takeaways"):
                try:
                    item["takeaways"] = json.loads(item["takeaways"])
                except Exception:
                    pass
            result.append(item)
        return result
    finally:
        conn.close()


def get_bookmark(bookmark_id: int, db_path=None) -> dict | None:
    """Retrieve a single bookmark by its ID."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, summary, url, takeaways, created_at FROM bookmarks WHERE id = ?",
            (bookmark_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        item = dict(row)
        if item.get("takeaways"):
            try:
                item["takeaways"] = json.loads(item["takeaways"])
            except Exception:
                pass
        return item
    finally:
        conn.close()


def delete_bookmark(bookmark_id: int, db_path=None) -> bool:
    """Delete a bookmark by its ID."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def is_bookmarked(title: str, db_path=None) -> bool:
    """Check if an article title is already bookmarked."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM bookmarks WHERE title = ? COLLATE NOCASE LIMIT 1", (title.strip(),))
        return cursor.fetchone() is not None
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
