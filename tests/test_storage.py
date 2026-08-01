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

        storage.conn.execute(
            "UPDATE articles SET updated_at = ? WHERE url = ?",
            ("2024-01-01T00:00:00", "https://one.example"),
        )
        storage.conn.execute(
            "UPDATE articles SET updated_at = ? WHERE url = ?",
            ("2026-01-01T00:00:00", "https://two.example"),
        )
        storage.conn.commit()

        updated_count = storage.mark_outdated_before("2025-01-01T00:00:00")

        assert updated_count == 1
        assert storage.get_status("https://one.example") == "outdated"
        assert storage.get_status("https://two.example") == "scored"
