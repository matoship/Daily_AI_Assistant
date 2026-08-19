import daily_assistant.eval.sanity as sanity
from daily_assistant.models import Article, ExpectedThreshold, Fixture, TriageResult


def test_load_fixtures_returns_fixture_list():
    fixtures = sanity.load_fixtures()

    assert isinstance(fixtures, list)
    assert len(fixtures) > 0
    assert set(["id", "article", "expected"]).issubset(fixtures[0].keys())


def test_check_fixture_thresholds():
    fixture = Fixture(
        id="example",
        article=Article(
            url="https://example.com/article",
            source="Example Source",
            title="Example Article",
            summary="Example summary",
        ),
        expected=ExpectedThreshold(min_relevance=5, max_relevance=8),
        note="Example fixture",
    )

    assert sanity.check_fixture(
        fixture,
        TriageResult(relevance=7, category="engineering", reason="On topic", story_hint="AI"),
    )
    assert not sanity.check_fixture(
        fixture,
        TriageResult(relevance=4, category="engineering", reason="Too low", story_hint="AI"),
    )
    assert not sanity.check_fixture(
        fixture,
        TriageResult(relevance=9, category="engineering", reason="Too high", story_hint="AI"),
    )


def test_run_sanity_uses_fixture_thresholds(monkeypatch):
    fixtures = [
        {
            "id": "demo",
            "article": {
                "url": "https://example.com/article",
                "source": "Example Source",
                "title": "Example Article",
                "summary": "Example summary",
            },
            "expected": {"min_relevance": 5, "max_relevance": 8},
        }
    ]

    def fake_triage_article(article, profile, client):
        return TriageResult(relevance=7, category="engineering", reason="On topic", story_hint="AI")

    monkeypatch.setattr(sanity, "triage_article", fake_triage_article)

    results = sanity.run_sanity(fixtures, {"identity": {}}, object())

    assert results == [
        {
            "id": "demo",
            "passed": True,
            "actual_relevance": 7,
            "article_title": "Example Article",
        }
    ]


def test_summarize_results_counts_pass_and_fail():
    results = [
        {"passed": True},
        {"passed": False},
        {"passed": True},
    ]

    assert sanity.summarize_results(results) == {"total": 3, "passed": 2, "failed": 1}


def test_main_returns_nonzero_when_fixture_fails(monkeypatch):
    fixtures = [{
        "id": "demo",
        "article": {
            "url": "https://example.com/article",
            "source": "Example Source",
            "title": "Example Article",
            "summary": "Example summary",
        },
        "expected": {"min_relevance": 10, "max_relevance": 10},
    }]

    monkeypatch.setattr(sanity, "load_fixtures", lambda path="": fixtures)

    import daily_assistant.profile as profile_module
    monkeypatch.setattr(profile_module, "load_profile", lambda: {"identity": {}})

    import daily_assistant.telemetry as telemetry_module
    monkeypatch.setattr(telemetry_module, "TrackedClient", lambda *args, **kwargs: object())

    import daily_assistant.config as config_module
    monkeypatch.setattr(config_module, "get_settings", lambda: type("Settings", (), {"anthropic_api_key": "test-key"})())

    def fake_triage_article(article, profile, client):
        return TriageResult(relevance=7, category="engineering", reason="Low", story_hint="AI")

    monkeypatch.setattr(sanity, "triage_article", fake_triage_article)

    assert sanity.main("ignored") == 1