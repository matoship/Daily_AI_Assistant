import feedparser
from daily_assistant.models import Source, Article
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def fetch_articles(source: Source) -> list[Article]:
    """
    Fetch articles from a given source using its RSS feed.
    """
    feed = feedparser.parse(source.url)
    articles: list[Article] = []
    if feed.bozo:
        logger.error(
            f"Error parsing feed for source {source.name}: {feed.bozo_exception}"
        )
        return articles
    if len(feed.entries) == 0:
        logger.warning(f"No entries found in feed for source {source.name}")
        return articles
    for entry in feed.entries:
        parsed = entry.get("published_parsed")
        if parsed:
            published_at = datetime(*parsed[:6])
        else:
            published_at = None
        article = Article(
            url=entry.link,
            source=source.name,
            title=entry.title,
            published_at=published_at,
            summary=entry.get("summary", ""),
        )
        logger.info(f"Fetched article: {article.title} from {source.name}")
        articles.append(article)

    logger.info(f"Finished fetching articles from {source.name}")
    return articles
