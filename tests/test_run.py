from types import SimpleNamespace

from daily_assistant import run as run_module
from daily_assistant.protocol import LLMError


class DummyStorage:
    def __init__(self):
        self.scored_urls = []
        self.finished_runs = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def mark_outdated_before(self, cutoff):
        return []

    def mark_scored(self, url):
        self.scored_urls.append(url)
        return None

    def store_triage_log(self, **kwargs):
        return None

    def mark_digested(self, url):
        return None

    def start_run(self):
        return "run-1"

    def finish_run(self, *args, **kwargs):
        self.finished_runs.append((args, kwargs))
        return None


class DummyClient:
    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.usage_by_model = {}


def test_run_passes_tracked_client_to_pipeline(monkeypatch):
    captured = {}
    fake_client = DummyClient()
    models = {"triage": "triage-model", "synthesis": "synthesis-model"}

    def fake_triage(article, profile, client, model):
        captured["triage_client"] = client
        captured["triage_model"] = model
        return SimpleNamespace(
            relevance=5,
            category="tech",
            title=article.title,
            reason="stubbed triage reason",
        )

    def fake_synthesize(selected_articles, profile, client, model):
        captured["synthesize_client"] = client
        captured["synthesize_model"] = model
        return []

    monkeypatch.setattr(run_module, "load_profile", lambda: {})
    monkeypatch.setattr(run_module, "load_sources", lambda: [])
    monkeypatch.setattr(run_module, "Storage", lambda: DummyStorage())
    monkeypatch.setattr(
        run_module,
        "ingest",
        lambda sources, storage: [
            SimpleNamespace(
                title="demo",
                url="https://example.com",
                source="test",
                published_at=None,
                summary="demo",
            )
        ],
    )
    monkeypatch.setattr(run_module, "triage_article", fake_triage)
    monkeypatch.setattr(
        run_module,
        "select_for_synthesis",
        lambda triaged_articles, threshold=5, top_n_per_category=5: [],
    )
    monkeypatch.setattr(run_module, "synthesize", fake_synthesize)
    def fake_build_client(args):
        captured["build_args"] = args
        return fake_client, models

    monkeypatch.setattr(run_module, "build_client", fake_build_client)

    run_module.run(True)

    assert captured["build_args"] is True
    assert captured["triage_client"] is fake_client
    assert captured["triage_model"] == models["triage"]
    assert captured["synthesize_client"] is fake_client
    assert captured["synthesize_model"] == models["synthesis"]


def test_run_continues_when_one_article_fails_triage(monkeypatch):
    storage = DummyStorage()
    fake_client = DummyClient()
    models = {"triage": "triage-model", "synthesis": "synthesis-model"}
    failed_article = SimpleNamespace(
        title="failed article",
        url="https://example.com/failed",
        source="test",
        published_at=None,
        summary="failed summary",
    )
    successful_article = SimpleNamespace(
        title="successful article",
        url="https://example.com/successful",
        source="test",
        published_at=None,
        summary="successful summary",
    )

    def fake_triage(article, profile, client, model):
        if article is failed_article:
            raise LLMError("temporary failure", provider="test", model=model)
        return SimpleNamespace(
            relevance=5,
            category="tech",
            title=article.title,
            reason="stubbed triage reason",
        )

    monkeypatch.setattr(run_module, "load_profile", lambda: {})
    monkeypatch.setattr(run_module, "load_sources", lambda: [])
    monkeypatch.setattr(run_module, "Storage", lambda: storage)
    monkeypatch.setattr(
        run_module,
        "ingest",
        lambda sources, storage: [failed_article, successful_article],
    )
    monkeypatch.setattr(run_module, "triage_article", fake_triage)
    monkeypatch.setattr(
        run_module,
        "select_for_synthesis",
        lambda triaged_articles, threshold=5, top_n_per_category=5: [],
    )
    monkeypatch.setattr(run_module, "synthesize", lambda *args: [])
    monkeypatch.setattr(
        run_module, "build_client", lambda args: (fake_client, models)
    )

    assert run_module.run(True) == []

    assert storage.scored_urls == [successful_article.url]
    assert storage.finished_runs[-1][1]["status"] == "completed"
