import sqlite3

class Storage:
    def __init__(self, db_path: str = "seen.db"):
        self.conn = sqlite3.connect(db_path)
        self.init_db()

    def init_db(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS seen_articles (
                url TEXT PRIMARY KEY,
                first_seen_at TEXT
            )
        ''')
        self.conn.commit()

    def mark_article_as_seen(self, url: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO seen_articles (url, first_seen_at)
            VALUES (?, datetime('now'))
        ''', (url,))
        self.conn.commit()

    def has_article_been_seen(self, url: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute('SELECT 1 FROM seen_articles WHERE url = ?', (url,))
        return cursor.fetchone() is not None

    def close(self) -> None:
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()          # reuse close() — one place that knows how to clean up