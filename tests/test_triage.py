from daily_assistant.triage import triage_article
from daily_assistant.models import Article
from daily_assistant.protocol import LLMResponse


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
        truncated=False,
    )
    mock_client = fake_llm_client(fake_response)

    # Call the triage_article function
    result = triage_article(article, profile, mock_client)

    # Assertions to check if the result is as expected
    assert result.relevance == 8
    assert result.category == "Technology"
    assert (
        result.reason
        == "The article is relevant to the user's interests in technology."
    )
