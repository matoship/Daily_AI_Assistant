from daily_assistant.models import Article
from daily_assistant.source import fetch_articles
from daily_assistant.storage import Storage

def ingest(feed_urls: list[str], storage: Storage) -> list[Article]:
    new_articles = []
    for feed_url in feed_urls:
        articles = fetch_articles(feed_url)
        for article in articles:
            if not storage.has_article_been_seen(article.url):
                storage.mark_article_as_seen(article.url)
                new_articles.append(article)
    return new_articles