
from src.daily_assistant.models import Article, TriageResult


def triage_article(article: Article, profile: dict, client: anthropic.Anthropic) -> TriageResult: ...
    