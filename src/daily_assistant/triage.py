from daily_assistant.models import Article, TriageResult
from anthropic import Anthropic
from daily_assistant.profile import category_options 

def triage_article(article: Article, profile: dict, client: Anthropic) -> TriageResult:
    """
    Triage an article based on the user's profile and return a TriageResult.
    """
    # Construct the prompt for the model
    prompt = f"""
    You are an AI assistant that helps triage news articles based on a user's profile.
    
    User Profile:
    {profile}
    
    Article:
    URL: {article.url}
    Source: {article.source}
    Title: {article.title}
    Published At: {article.published_at}
    Summary: {article.summary}
    
    Please provide a relevance score (0-10), a category, a reason for your decision, and any story hints.
    """
    categories = category_options(profile) + ["other"]
    # Call the model
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        temperature=0,
        tools=[{"name": "provide_triage_result", 
                "description": "Provide a triage result with relevance, category, reason, and story hints",
               "input_schema": {
                    "type": "object",
                    "properties": {
                        "relevance": {"type": "integer","description": "Relevance score (0-10)"},
                        "category": {"type": "string", "enum": categories, "description": "Category of the article"},
                        "reason": {"type": "string", "description": "Reason for the triage decision"},
                        "story_hint": {"type": "string", "description": "Any story hints"}
                    },
                    "required": ["relevance", "category", "reason", "story_hint"]
                }
               }],
        tool_choice={"type": "tool", "name": "provide_triage_result"},
        messages=[{"role": "user", "content": prompt}]
        )

    tool_use_block = None
    for block in response.content:
        if block.type == "tool_use":
            tool_use_block = block
            break

    if tool_use_block is None:
        raise ValueError("Claude did not return a tool_use block")

    return TriageResult(**tool_use_block.input)