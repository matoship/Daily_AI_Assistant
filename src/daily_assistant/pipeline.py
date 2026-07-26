from daily_assistant.models import Source
from daily_assistant.source import fetch_articles
from daily_assistant.storage import Storage

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
        articles = fetch_articles(source)
        for article in articles:
            if not storage.has_article_been_seen(article.url):
                storage.mark_article_as_seen(article.url)
                new_articles.append(article)
    return new_articles