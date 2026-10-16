from daily_assistant.models import Article, TriageResult
from daily_assistant.synthesize import synthesize
from daily_assistant.profile import load_profile
from daily_assistant.protocol import LLMProtocolError, LLMResponse
import pytest
from pydantic import ValidationError


def test_synthesize(fake_llm_client):
    # Mock articles and triage results
    articles = [
        Article(
            url="https://example.com/news/article1",
            source="Example News",
            title="Breaking News: Example Event",
            published_at="2024-06-01T12:00:00Z",
            summary="This is a summary of the example news article.",
        ),
        Article(
            url="https://example.com/news/article2",
            source="Example News",
            title="Another News: Example Event 2",
            published_at="2024-06-02T12:00:00Z",
            summary="This is a summary of another example news article.",
        ),
    ]

    triage_results = [
        TriageResult(
            relevance=8,
            category="Technology",
            reason="Relevant to user's interests.",
            story_hint="Follow up on technology trends.",
        ),
        TriageResult(
            relevance=5,
            category="Politics",
            reason="Somewhat relevant to user's interests.",
            story_hint="Consider political implications.",
        ),
    ]

    triaged = list(zip(articles, triage_results))

    # Load a mock profile
    profile = load_profile()

    fake_response = LLMResponse(
        tool_input={
            "digest_items": [
                {
                    "headline": "Synthesized Headline",
                    "summary": "Synthesized Summary",
                    "why_it_matters": "Synthesized Why It Matters",
                    "category": "Synthesized Category",
                    "article_urls": [
                        "https://example.com/news/article1",
                        "https://example.com/news/article2",
                    ],
                }
            ]
        },
        model="test-model",
        input_tokens=0,
        output_tokens=0,
        provider="test",
    )
    mock_client = fake_llm_client(fake_response)

    # Call the synthesize function
    digest_items = synthesize(triaged, profile, mock_client, model="test-model")

    # Assertions to check if the digest items are as expected
    assert len(digest_items) == 1
    assert digest_items[0].headline == "Synthesized Headline"
    assert digest_items[0].summary == "Synthesized Summary"
    assert digest_items[0].why_it_matters == "Synthesized Why It Matters"
    assert digest_items[0].category == "Synthesized Category"


@pytest.mark.parametrize("field", ["headline", "article_urls"])
@pytest.mark.parametrize("invalid_kind", ["missing", "wrong_type"])
def test_synthesize_wraps_validation_error(fake_llm_client, field, invalid_kind):
    article = Article(
        url="https://example.com/news", source="test", title="News", summary="News"
    )
    triage = TriageResult(relevance=5, category="other", reason="Relevant")
    valid_item = {
        "headline": "News",
        "summary": "Summary",
        "why_it_matters": "Relevant",
        "category": "other",
        "article_urls": [article.url],
    }
    invalid_item = valid_item.copy()
    if invalid_kind == "missing":
        del invalid_item[field]
    else:
        invalid_item[field] = 123
    response = LLMResponse(
        # A later invalid item must raise rather than return a partial digest.
        tool_input={"digest_items": [valid_item, invalid_item]},
        model="returned-model",
        input_tokens=1,
        output_tokens=1,
        provider="test-provider",
    )

    with pytest.raises(LLMProtocolError, match="Invalid synthesis result") as exc_info:
        synthesize(
            [(article, triage)], {}, fake_llm_client(response), model="requested-model"
        )

    error = exc_info.value
    assert error.provider == "test-provider"
    assert error.model == "returned-model"
    assert isinstance(error.__cause__, ValidationError)
    assert error.__cause__.errors()[0]["loc"] == (field,)
