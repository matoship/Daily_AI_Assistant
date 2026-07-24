from daily_assistant.models import Source,Article
from daily_assistant.storage import Storage
from daily_assistant.pipeline import ingest

def test_ingest(monkeypatch):
    # Mock sources
    sources: list[Source] = [
        {
            "url": "http://example.com/rss",
            "name": "Example Source",
            "justification": "Test source for unit testing"
        }
    ]
    fake_articles = [
        Article(
            url="http://example.com/article1",
            source="Example Source",
            title="Test Article 1",
            summary="Summary 1",
        )
    ]
    monkeypatch.setattr("daily_assistant.pipeline.fetch_articles", lambda url: fake_articles)

    with Storage(":memory:") as storage:
        
        # Call the ingest function
        first = ingest(sources, storage)
        second = ingest(sources, storage)
        
    assert len(first) == 1  # First ingestion should store the article
    assert len(second) == 0  # Second ingestion should not store the same article again

    
    