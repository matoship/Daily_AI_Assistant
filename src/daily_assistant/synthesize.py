from daily_assistant.models import Article, TriageResult, DigestItem
from daily_assistant.protocol import LLMResponse, LLMClient


def synthesize(
    selected_articles: list[tuple[Article, TriageResult]],
    profile: dict,
    client: LLMClient,
) -> list[DigestItem]:
    """
    Synthesize selected articles into digest items using the Anthropic API wrapped in LLMclient.

    Args:
        selected_articles (list[tuple[Article, TriageResult]]): A list of tuples containing articles and their corresponding triage results.
        profile (dict): The user profile containing preferences and interests.
        client (LLMclient): An instance of the wrapped Anthropic API client.

    Returns:
        list[DigestItem]: A list of synthesized digest items.
    """
    if not selected_articles:
        return []

    prompt = f"""
    You are a news summarization assistant. 
    Please summarize the following articles into a digest item. 
    The user is interested in the following topics: {", ".join(profile.get("topics", {}).keys())}.
    Here is my identity: {profile.get("identity", {})}

    here are selected articles and their triage results:
    {[(article.title, result.relevance, result.category, article.url) for article, result in selected_articles]}
    
    Please provide:
    1. A concise headline.
    2. A brief summary of the article.
    3. Why it matters to me based on my interests.
    4. The category of the article based on my interests.
    5. The URL of the articles.
    6.if several articles cover the same event, merge them into one entry; if they're unrelated, give each its own entry.

    """

    response: LLMResponse = client.create(
        model="claude-sonnet-5",
        max_tokens=800 * len(selected_articles),
        prompt=prompt,
        tool_name="synthesize_article",
        tool_description="Synthesize an article into a digest item based on the user's profile",
        tool_schema={
            "type": "object",
            "properties": {
                "digest_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "headline": {"type": "string"},
                            "summary": {"type": "string"},
                            "why_it_matters": {"type": "string"},
                            "category": {"type": "string"},
                            "article_urls": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": [
                            "headline",
                            "summary",
                            "why_it_matters",
                            "category",
                            "article_urls",
                        ],
                    },
                }
            },
            "required": ["digest_items"],
        },
    )

    digest_items = []
    for item in response.tool_input["digest_items"]:
        digest_items.append(DigestItem(**item))

    return digest_items
