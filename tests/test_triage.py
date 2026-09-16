from daily_assistant.triage import triage_article
from daily_assistant.models import Article
from daily_assistant.protocol import LLMProtocolError, LLMResponse
import pytest
from pydantic import ValidationError


def test_triage_article(fake_llm_client):
    # Mock Article and profile
    article = Article(
        url="https://example.com/news/article1",
        source="Example News",
        title="Breaking News: Example Event",
        published_at="2024-06-01T12:00:00Z",
        summary="This is a summary of the example news article.",
    )
    profile = {
        "identity": {"name": "John Doe", "age": 30},
        "interests": ["technology", "politics"],
        "location": {"country": "USA"},
    }

    fake_response = LLMResponse(
        tool_input={
            "relevance": 8,
            "category": "Technology",
            "reason": "The article is relevant to the user's interests in technology.",
            "story_hint": "Follow up on the technology trends mentioned.",
        },
        model="test-model",
        input_tokens=0,
        output_tokens=0,
        provider="test",
    )
    mock_client = fake_llm_client(fake_response)

    # Call the triage_article function
    result = triage_article(article, profile, mock_client, model="test-model")

    # Assertions to check if the result is as expected
    assert result.relevance == 8
    assert result.category == "Technology"
    assert (
        result.reason
        == "The article is relevant to the user's interests in technology."
    )


@pytest.mark.parametrize(
    "invalid_fields, field",
    [
        ({"relevance": -1}, "relevance"),
        ({"relevance": 11}, "relevance"),
        ({"relevance": "not a score"}, "relevance"),
        ({"reason": None}, "reason"),
    ],
)
def test_triage_wraps_validation_error(fake_llm_client, invalid_fields, field):
    article = Article(
        url="https://example.com/news", source="test", title="News", summary="News"
    )
    response = LLMResponse(
        tool_input={"relevance": 5, "category": "other", "reason": "Relevant"}
        | invalid_fields,
        model="returned-model",
        input_tokens=1,
        output_tokens=1,
        provider="test-provider",
    )

    with pytest.raises(LLMProtocolError, match="Invalid triage result") as exc_info:
        triage_article(article, {}, fake_llm_client(response), model="requested-model")

    error = exc_info.value
    assert error.provider == "test-provider"
    assert error.model == "returned-model"
    assert isinstance(error.__cause__, ValidationError)
    assert error.__cause__.errors()[0]["loc"] == (field,)


@pytest.mark.parametrize("relevance", [0, 10])
def test_triage_accepts_relevance_boundaries(fake_llm_client, relevance):
    article = Article(
        url="https://example.com/news", source="test", title="News", summary="News"
    )
    response = LLMResponse(
        tool_input={"relevance": relevance, "category": "other", "reason": "Relevant"},
        model="test-model",
        input_tokens=1,
        output_tokens=1,
        provider="test",
    )

    result = triage_article(article, {}, fake_llm_client(response), model="test-model")

    assert result.relevance == relevance
