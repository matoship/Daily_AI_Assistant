import sqlite3
from daily_assistant.models import ArticleStatus
from datetime import datetime, timezone


class Storage:
    def __init__(self, db_path: str = "seen.db"):
        self.conn = sqlite3.connect(db_path)
        self.init_db()

    def init_db(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                url TEXT PRIMARY KEY,                
                status TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                first_seen_at TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def upsert_status(self, url: str, status: ArticleStatus) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO articles (url, status, first_seen_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                status = excluded.status,
                updated_at = excluded.updated_at
            """,
            (url, status, datetime.now(timezone.utc).isoformat(),datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()

    def get_status(self, url: str) -> ArticleStatus | None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT status FROM articles WHERE url = ?
            """,
            (url,),
        )
        row = cursor.fetchone()
        return row[0] if row is not None else None

    def mark_outdated_before(self, cutoff_iso: str) -> int:
        """Mark articles WHERE first_seen_at < ? AND status in "fetched" as outdated"""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE articles
            SET status = 'outdated', updated_at = ?
            WHERE first_seen_at < ? AND status = 'fetched'
            """,
            (cutoff_iso,datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()
        return cursor.rowcount

    def mark_outdated(self, url: str) -> None:
        self.upsert_status(url, "outdated")

    def mark_digested(self, url: str) -> None:
        self.upsert_status(url, "digested")

    def mark_scored(self, url: str) -> None:
        self.upsert_status(url, "scored")

    def mark_fetched(self, url: str) -> None:
        self.upsert_status(url, "fetched")


    def close(self) -> None:
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()