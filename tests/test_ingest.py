from daily_assistant.models import Article
from daily_assistant.storage import Storage
from daily_assistant.pipeline import ingest

def test_ingest_dedups(monkeypatch):
    fake_articles = [
        Article(url="http://a.com/1", source="t", title="One", summary=""),
        Article(url="http://a.com/2", source="t", title="Two", summary=""),
    ]
    # replace the real fetch_articles that ingest calls with a fake that returns our list
    monkeypatch.setattr("daily_assistant.pipeline.fetch_articles", lambda url: fake_articles)

    with Storage(":memory:") as storage:
        first = ingest(["any-url"], storage)      # what should this return?
        second = ingest(["any-url"], storage)     # and this?
    # write the asserts: first has 2, second has 0
    assert len(first) == 2
    assert len(second) == 0