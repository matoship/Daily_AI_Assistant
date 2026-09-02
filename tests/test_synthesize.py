from daily_assistant.models import Article, TriageResult
from daily_assistant.synthesize import synthesize
from daily_assistant.profile import load_profile
from daily_assistant.protocol import LLMResponse


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
    )
    mock_client = fake_llm_client(fake_response)

    # Call the synthesize function
    digest_items = synthesize(triaged, profile, mock_client)

    # Assertions to check if the digest items are as expected
    assert len(digest_items) == 1
    assert digest_items[0].headline == "Synthesized Headline"
    assert digest_items[0].summary == "Synthesized Summary"
    assert digest_items[0].why_it_matters == "Synthesized Why It Matters"
    assert digest_items[0].category == "Synthesized Category"
