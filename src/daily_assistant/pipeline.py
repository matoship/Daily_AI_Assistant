from daily_assistant.models import Source
from daily_assistant.source import fetch_articles
from daily_assistant.storage import Storage
import logging
logger = logging.getLogger(__name__)

def ingest(sources: list[dict], storage: Storage):
    """
    Ingest articles from a list of sources and store them in the provided storage.
    
    Args:
        sources (list[dict]): A list of source dictionaries, each containing 'url', 'name', and 'justification'.
        storage (Storage): An instance of the Storage class to store the ingested articles.
    """
    new_articles = []

    for source_dict in sources:
        source = Source(**source_dict)
        logger.info(f"Fetching articles from source: {source.name} ({source.url})")
        articles = fetch_articles(source)
        for article in articles:
            status = storage.get_status(article.url)
            if status is None or status == "fetched":
                storage.mark_fetched(article.url)
                new_articles.append(article)

    return new_articles