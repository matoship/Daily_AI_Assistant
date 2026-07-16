import feedparser
from daily_assistant.models import Article
from datetime import datetime


def fetch_articles(feed_url: str) -> list[Article]: 
    feed = feedparser.parse(feed_url)
    articles = []
    for entry in feed.entries:
        article = Article(
            url=entry.link,
            source=feed.feed.title,
            title=entry.title,
            published_at=datetime(*entry.published_parsed[:6]) if entry.get('published_parsed') else None,
            summary=entry.get('summary', "")
        )
        articles.append(article)
    return articles
