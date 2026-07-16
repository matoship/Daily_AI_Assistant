from daily_assistant.storage import Storage
from daily_assistant.models import Article

def test_storage_add_and_retrieve_article():
    # Initialize the storage
    with Storage(":memory:") as storage:  # Use in-memory database for testing
        # Create a test article
        test_article = Article(
            url="https://example.com/test-article",
            source="Example Source",
            title="Test Article",
            published_at=None,
            summary="This is a test article."
        )

        # Mark the article as seen
        storage.mark_article_as_seen(test_article.url)

        # Check if the article has been marked as seen
        assert storage.has_article_been_seen(test_article.url)

        # Check if an unseen article returns False
        assert not storage.has_article_been_seen("https://example.com/unseen-article")
