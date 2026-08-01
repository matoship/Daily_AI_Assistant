from daily_assistant.source import fetch_articles
from daily_assistant.models import Source
import feedparser
from datetime import datetime

def test_fetch_articles(monkeypatch):
    # Create a mock source
    source = Source(
        url="http://example.com/rss",
        name="Example Source",
        justification="Test source for unit testing"
    )

    # Mock the feedparser.parse function to return a controlled response
    class MockFeed:
        def __init__(self):
            self.bozo = False
            self.entries = [
                feedparser.FeedParserDict({
                    "link": "http://example.com/article1",
                    "title": "Test Article 1",
                    "published_parsed": (2024, 6, 1, 12, 0, 0, 0, 0, 0),
                    "summary": "Summary of article 1",
                }),
                feedparser.FeedParserDict({
                    "link": "http://example.com/article2",
                    "title": "Test Article 2",
                    "published_parsed": (2024, 6, 2, 12, 0, 0, 0, 0, 0),
                    "summary": "Summary of article 2",
                }),
            ]

    def mock_parse(url):
        return MockFeed()

    monkeypatch.setattr(feedparser, "parse", mock_parse)
    articles = fetch_articles(source)
    assert len(articles) == 2
    assert articles[0].url == "http://example.com/article1"
    assert articles[0].title == "Test Article 1"
    assert articles[0].published_at == datetime(2024, 6, 1, 12, 0, 0)
    assert articles[1].url == "http://example.com/article2"
    assert articles[1].title == "Test Article 2"
    assert articles[1].published_at == datetime(2024, 6, 2, 12, 0, 0)