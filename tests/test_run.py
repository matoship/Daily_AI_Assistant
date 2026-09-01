from types import SimpleNamespace

from daily_assistant import run as run_module


class DummyStorage:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def mark_outdated_before(self, cutoff):
        return []

    def mark_scored(self, url):
        return None

    def mark_digested(self, url):
        return None

    def start_run(self):
        return "run-1"

    def finish_run(self, *args, **kwargs):
        return None


class DummyClient:
    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.usage_by_model = {}


def test_run_passes_tracked_client_to_pipeline(monkeypatch):
    captured = {}
    fake_client = DummyClient()

    def fake_triage(article, profile, client):
        captured["triage_client"] = client
        return SimpleNamespace(relevance=5, category="tech", title=article.title)

    def fake_synthesize(selected_articles, profile, client):
        captured["synthesize_client"] = client
        return []

    monkeypatch.setattr(run_module, "load_profile", lambda: {})
    monkeypatch.setattr(run_module, "load_sources", lambda: [])
    monkeypatch.setattr(run_module, "Storage", lambda: DummyStorage())
    monkeypatch.setattr(run_module, "ingest", lambda sources, storage: [SimpleNamespace(title="demo", url="https://example.com", source="test", published_at=None, summary="demo")])
    monkeypatch.setattr(run_module, "triage_article", fake_triage)
    monkeypatch.setattr(run_module, "select_for_synthesis", lambda triaged_articles, threshold=5, top_n_per_category=5: [])
    monkeypatch.setattr(run_module, "synthesize", fake_synthesize)
    monkeypatch.setattr(run_module, "build_client", lambda: fake_client)

    run_module.run()

    assert captured["triage_client"] is fake_client
    assert captured["synthesize_client"] is fake_client
