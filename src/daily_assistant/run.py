from daily_assistant.triage import triage_article
from daily_assistant.selection import select_for_synthesis
from daily_assistant.synthesize import synthesize
from daily_assistant.pipeline import ingest
from daily_assistant.profile import load_profile,load_sources
from daily_assistant.storage import Storage
from anthropic import Anthropic
from daily_assistant.config import get_settings

def run():
    """
    Run the daily assistant pipeline:
    1. Load user profile and sources.
    2. Ingest articles from sources.
    3. Triage articles based on relevance to the user's profile.
    4. Select articles for synthesis.
    5. Synthesize a digest from selected articles.
    """
    # Load user profile and sources
    profile = load_profile()
    sources = load_sources()

    # Initialize the Anthropic client
    client = Anthropic(api_key=get_settings().anthropic_api_key)

    # Initialize storage (assuming a Storage class is defined elsewhere)
    with Storage() as storage:
        # Ingest articles from sources
        new_articles = ingest(sources, storage)
    
    # Triage articles based on relevance to the user's profile
    triaged_articles = [(article, triage_article(article, profile, client)) for article in new_articles]
    
    # Select articles for synthesis
    selected_articles = select_for_synthesis(triaged_articles, threshold=5, top_n=5)
    
    # Synthesize a digest from selected articles
    digest = synthesize(selected_articles,profile,client)
    
    return digest