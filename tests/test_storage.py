from daily_assistant.storage import Storage
from daily_assistant.models import Article


def test_storage_add_and_retrieve_article():
    with Storage(":memory:") as storage:
        test_article = Article(
            url="https://example.com/test-article",
            source="Example Source",
            title="Test Article",
            published_at=None,
            summary="This is a test article.",
        )

        storage.mark_outdated(test_article.url)
        assert storage.get_status(test_article.url) == "outdated"


def test_mark_outdated_before_returns_updated_rows():
    with Storage(":memory:") as storage:
        storage.upsert_status("https://one.example", "fetched")
        storage.upsert_status("https://two.example", "scored")
        storage.upsert_status("https://three.example", "fetched")

        storage.conn.execute(
            "UPDATE articles SET first_seen_at = ? WHERE url = ?",
            ("2024-01-01T00:00:00", "https://one.example"),
        )
        storage.conn.execute(
            "UPDATE articles SET first_seen_at = ? WHERE url = ?",
            ("2024-01-01T00:00:00", "https://two.example"),
        )
        storage.conn.commit()

        updated_count = storage.mark_outdated_before("2025-01-01T00:00:00")

        assert updated_count == 1
        assert storage.get_status("https://one.example") == "outdated"
        assert storage.get_status("https://two.example") == "scored"
        assert storage.get_status("https://three.example") == "fetched"

def test_save_and_retrieve_triage_log():
    with Storage(":memory:") as storage:
        test_article = Article(
            url="https://example.com/test-article",
            source="Example Source",
            title="Test Article",
            published_at=None,
            summary="This is a test article.",
        )
        storage.store_triage_log(
            url=test_article.url,
            source=test_article.source,
            title=test_article.title,
            summary=test_article.summary,
            relevance=5,
            category="test_category",
            reason="Test reason"
        )

        cursor = storage.conn.cursor()
        cursor.execute("SELECT * FROM triage_logs WHERE url = ?", (test_article.url,))
        row = cursor.fetchone()

        assert row is not None
        assert row[1] == test_article.url
        assert row[2] == test_article.source
        assert row[3] == test_article.title
        assert row[4] == test_article.summary
        assert row[5] == 5
        assert row[6] == "test_category"
        assert row[7] == "Test reason"

        triage_logs = storage.get_triage_logs()
        assert len(triage_logs) == 1
        assert triage_logs[0]["url"] == test_article.url
        assert triage_logs[0]["source"] == test_article.source
        assert triage_logs[0]["title"] == test_article.title
        assert triage_logs[0]["summary"] == test_article.summary
        assert triage_logs[0]["relevance"] == 5
        assert triage_logs[0]["category"] == "test_category"
        assert triage_logs[0]["reason"] == "Test reason"
