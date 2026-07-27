
from daily_assistant.models import Article, TriageResult, DigestItem
from anthropic import Anthropic

def synthesize(selected_articles: list[tuple[Article, TriageResult]],profile:dict,client:Anthropic ) -> list[DigestItem]:
    """
    Synthesize selected articles into digest items using the Anthropic API.
    
    Args:
        selected_articles (list[tuple[Article, TriageResult]]): A list of tuples containing articles and their corresponding triage results.
        profile (dict): The user profile containing preferences and interests.
        client (Anthropic): An instance of the Anthropic API client.
    
    Returns:
        list[DigestItem]: A list of synthesized digest items.
    """
    digest_items = []
    

    prompt = f"""
    You are a news summarization assistant. 
    Please summarize the following articles into a digest item. 
    The user is interested in the following topics: {', '.join(profile.get('topics', {}).keys())}.
    
    here are selected articles and their triage results:
    {[(article.title, result.relevance, result.category, article.url) for article, result in selected_articles]}
    
    Please provide:
    1. A concise headline.
    2. A brief summary of the article.
    3. Why it matters to the user based on their interests.
    4. The category of the article based on the user's interests.
    5. The URL of the articles.
    6.if several articles cover the same event, merge them into one entry; if they're unrelated, give each its own entry.

    Format your response as a JSON object with keys: headline, summary, why_it_matters, category, article_urls.
    """
    
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=800 * len(selected_articles),
        tools=[{"name": "synthesize_article", 
                "description": "Synthesize an article into a digest item based on the user's profile",
                "input_schema": {
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
                                "article_urls": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["headline", "summary", "why_it_matters", "category", "article_urls"]
                        },
                    }
                },
                "required": ["digest_items"],
            }}],
            tool_choice={"type": "tool", "name": "synthesize_article"},
            messages=[{"role": "user", "content": prompt}])

    tool_use_block = None
    for block in response.content:
        if block.type == "tool_use":
            tool_use_block = block
            break

    if tool_use_block is None:
        raise ValueError("Claude did not return a tool_use block")
    
    for item in tool_use_block.input["digest_items"]: digest_items.append(DigestItem(**item))

    return digest_items