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
        cursor.execute(
            """
                CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                articles_fetched INTEGER,
                articles_scored INTEGER,
                articles_relevant INTEGER,
                articles_digested INTEGER,
                total_input_tokens INTEGER,
                total_output_tokens INTEGER,
                estimated_cost_usd REAL,
                status TEXT NOT NULL,
                error_message TEXT
            )
            """
        )
        self.conn.commit()

    def start_run(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO runs (started_at, status)
            VALUES (?, ?)
            """,
            (datetime.now(timezone.utc).isoformat(), "running"),
        )
        self.conn.commit()
        return cursor.lastrowid

    def finish_run(self, run_id: int, **metrics) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE runs
            SET finished_at = ?, 
                articles_fetched = ?, 
                articles_scored = ?, 
                articles_relevant = ?, 
                articles_digested = ?, 
                total_input_tokens = ?, 
                total_output_tokens = ?, 
                estimated_cost_usd = ?, 
                status = ?, 
                error_message = ?
            WHERE id = ?
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                metrics.get("articles_fetched"),
                metrics.get("articles_scored"),
                metrics.get("articles_relevant"),
                metrics.get("articles_digested"),
                metrics.get("total_input_tokens"),
                metrics.get("total_output_tokens"),
                metrics.get("estimated_cost_usd"),
                metrics.get("status", "completed"),
                metrics.get("error_message"),
                run_id,
            ),
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
            SET status = 'outdated', updated_at = :now
            WHERE first_seen_at < :cutoff AND status = 'fetched'
            """,
            {"now":datetime.now(timezone.utc).isoformat(), "cutoff": cutoff_iso},
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