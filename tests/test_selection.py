from daily_assistant.selection import select_for_synthesis
from daily_assistant.models import Article, TriageResult


def test_select_articles():
    # Mock articles and triage results
    articles = [
        Article(
            title="Article 1",
            url="http://example.com/1",
            published_at=None,
            source="Source 1",
            summary="Summary 1",
        ),
        Article(
            title="Article 2",
            url="http://example.com/2",
            published_at=None,
            source="Source 2",
            summary="Summary 2",
        ),
        Article(
            title="Article 3",
            url="http://example.com/3",
            published_at=None,
            source="Source 3",
            summary="Summary 3",
        ),
        Article(
            title="Article 4",
            url="http://example.com/4",
            published_at=None,
            source="Source 4",
            summary="Summary 4",
        ),
        Article(
            title="Article 5",
            url="http://example.com/5",
            published_at=None,
            source="Source 5",
            summary="Summary 5",
        ),
        Article(
            title="Article 6",
            url="http://example.com/6",
            published_at=None,
            source="Source 6",
            summary="Summary 6",
        ),
        Article(
            title="Article 7",
            url="http://example.com/7",
            published_at=None,
            source="Source 7",
            summary="Summary 7",
        ),
        Article(
            title="Article 8",
            url="http://example.com/8",
            published_at=None,
            source="Source 8",
            summary="Summary 8",
        ),
        Article(
            title="Article 9",
            url="http://example.com/9",
            published_at=None,
            source="Source 9",
            summary="Summary 9",
        ),
    ]

    category_option = ["engineering", "immigration"]
    triage_results = [
        TriageResult(
            relevance=9,
            category=category_option[0],
            reason="Highly relevant",
            story_hint="Tech news",
        ),
        TriageResult(
            relevance=8,
            category=category_option[0],
            reason="Highly relevant",
            story_hint="Tech news",
        ),
        TriageResult(
            relevance=7,
            category=category_option[0],
            reason="Moderately relevant",
            story_hint="Health news",
        ),
        TriageResult(
            relevance=6,
            category=category_option[0],
            reason="Moderately relevant",
            story_hint="Health news",
        ),
        TriageResult(
            relevance=6,
            category=category_option[0],
            reason="Moderately relevant",
            story_hint="Science news",
        ),
        TriageResult(
            relevance=4,
            category=category_option[0],
            reason="Low relevance",
            story_hint="Science news",
        ),
        TriageResult(
            relevance=3,
            category=category_option[0],
            reason="Low relevance",
            story_hint="Business news",
        ),
        TriageResult(
            relevance=2,
            category=category_option[0],
            reason="Low relevance",
            story_hint="Business news",
        ),
        TriageResult(
            relevance=7,
            category=category_option[1],
            reason="Moderately relevant",
            story_hint="Sports news",
        ),
    ]

    triaged = list(zip(articles, triage_results))
    selected_articles = select_for_synthesis(triaged, 5, 3)

    category_option_one = 0
    category_option_two = 0
    for _article, triage_results in selected_articles:
        if triage_results.category == "engineering":
            category_option_one += 1
        if triage_results.category == "immigration":
            category_option_two += 1

    assert category_option_one == 3
    assert category_option_two == 1


def test_select_articles_with_no_relevant_articles():
    # Mock articles and triage results with low relevance
    articles = [
        Article(
            title="Article 1",
            url="http://example.com/1",
            published_at=None,
            source="Source 1",
            summary="Summary 1",
        ),
        Article(
            title="Article 2",
            url="http://example.com/2",
            published_at=None,
            source="Source 2",
            summary="Summary 2",
        ),
    ]

    triage_results = [
        TriageResult(
            relevance=3, category="Tech", reason="Low relevance", story_hint="Tech news"
        ),
        TriageResult(
            relevance=4,
            category="Health",
            reason="Low relevance",
            story_hint="Health news",
        ),
    ]

    triaged = list(zip(articles, triage_results))
    selected_articles = select_for_synthesis(triaged, 6, 2)

    # Check that no articles are selected
    assert len(selected_articles) == 0
