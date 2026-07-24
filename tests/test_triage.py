from daily_assistant.triage import triage_article
from daily_assistant.models import Article
from types import SimpleNamespace



def test_triage_article():
    # Mock Article and profile
    article =  Article(
        url="https://example.com/news/article1",
        source="Example News",
        title="Breaking News: Example Event",
        published_at="2024-06-01T12:00:00Z", 
        summary="This is a summary of the example news article."
    )
    profile = {
        "identity": {"name": "John Doe", "age": 30},
        "interests": ["technology", "politics"],
        "location": {"country": "USA"}
    }

    fake_block = SimpleNamespace(
    type="tool_use",
    input={"relevance": 8, "category": "Technology",
            "reason": "The article is relevant to the user's interests in technology.", 
            "story_hint": "Follow up on the technology trends mentioned."},
    )
    fake_response = SimpleNamespace(content=[fake_block])

    # Mock the Anthropic client
    class MockMessages:
        def create(self, model, max_tokens, temperature, tools, tool_choice, messages):
            # Return a mock response that simulates the model's output
            return fake_response
    class MockAnthropicClient:
        def __init__(self):
            self.messages = MockMessages()
            

    mock_client = MockAnthropicClient()

    # Call the triage_article function
    result = triage_article(article, profile, mock_client)



    # Assertions to check if the result is as expected
    assert result.relevance == 8
    assert result.category == "Technology"
    assert result.reason == "The article is relevant to the user's interests in technology."
    assert result.story_hint == "Follow up on the technology trends mentioned."