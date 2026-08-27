from daily_assistant.models import Article
from daily_assistant.pipeline import ingest
from daily_assistant.storage import Storage


def test_ingest(monkeypatch):
    sources: list[dict] = [
        {
            "url": "http://example.com/rss",
            "name": "Example Source",
            "justification": "Test source for unit testing",
        }
    ]
    source2: list[dict] = [
        {
            "url": "http://example.com/rss2",
            "name": "Example Source 2",
            "justification": "Test source for unit testing",
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
    monkeypatch.setattr(
        "daily_assistant.pipeline.fetch_articles",
        lambda source: fake_articles,
    )

    with Storage(":memory:") as storage:
        first = ingest(sources, storage)
        second = ingest(source2, storage)

        assert len(first) == 1
        assert first[0].url == fake_articles[0].url
        assert len(second) == 1
        assert second[0].url == fake_articles[0].url
        assert storage.get_status(fake_articles[0].url) == "fetched"
        storage.mark_scored(fake_articles[0].url)
        third = ingest(sources, storage) 
        assert len(third) == 0
