import feedparser
from daily_assistant.models import Source, Article
from datetime import datetime

def fetch_articles(source:Source) -> list[Article]:
    """
    Fetch articles from a given source using its RSS feed.
    """
    feed = feedparser.parse(source.url)
    articles = []
    
    for entry in feed.entries:
        published_at = None
        if 'published' in entry:
            published_at = datetime(*entry.published_parsed[:6])
        
        article = Article(
            url=entry.link,
            source=source.name,
            title=entry.title,
            published_at=published_at,
            summary=entry.summary
        )
        articles.append(article)
    
    return articles
