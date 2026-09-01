from daily_assistant.models import Article, TriageResult
from daily_assistant.protocol import LLMResponse,LLMClient
from daily_assistant.profile import category_options 

def triage_article(article: Article, profile: dict, client: LLMClient) -> TriageResult:
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
    response: LLMResponse = client.create(
    model = "claude-haiku-4-5-20251001",
    max_tokens = 600,
    prompt = prompt,
    tool_name = "provide_triage_result",
    tool_description="Provide a triage result with relevance, category, reason, and story hints",
    tool_schema={
                    "type": "object",
                    "properties": {
                        "relevance": {"type": "integer","description": "Relevance score (0-10)"},
                        "category": {"type": "string", "enum": categories, "description": "Category of the article"},
                        "reason": {"type": "string", "description": "Reason for the triage decision"},
                    },
                    "required": ["relevance", "category", "reason", ]
                },
     temperature=0,

    )


    return TriageResult(**response.tool_input)