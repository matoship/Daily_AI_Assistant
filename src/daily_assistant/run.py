from daily_assistant import storage
from daily_assistant.telemetry import TrackedClient, estimate_cost
from daily_assistant.triage import triage_article
from daily_assistant.selection import select_for_synthesis
from daily_assistant.synthesize import synthesize
from daily_assistant.pipeline import ingest
from daily_assistant.profile import load_profile,load_sources
from daily_assistant.storage import Storage
from anthropic import Anthropic
from daily_assistant.config import get_settings
from datetime import timedelta,datetime,timezone
import logging
logger = logging.getLogger(__name__)

def run():
    """
    Run the daily assistant pipeline:
    1. Load user profile and sources.
    2. Ingest articles from sources.
    3. Triage articles based on relevance to the user's profile.
    4. Select articles for synthesis.
    5. Synthesize a digest from selected articles.
    """

    logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
    logging.getLogger("httpx").setLevel(logging.WARNING) 
    # Load user profile and sources
    profile = load_profile()
    sources = load_sources()

    # Initialize the Anthropic client
    tracked_client = TrackedClient(Anthropic(api_key=get_settings().anthropic_api_key))

    # Initialize storage (assuming a Storage class is defined elsewhere)
    with Storage() as storage:
        run_id = storage.start_run()
        new_articles = [] 
        triaged_articles = [] 
        selected_articles = []
        digested_count = 0
        try:
            outdated=storage.mark_outdated_before((datetime.now(timezone.utc) - timedelta(hours=48)).isoformat())
            logger.info(f"Marked {outdated} articles as outdated in storage.")
            # Ingest articles from sources
            new_articles = ingest(sources, storage)
            logger.info(f"Total new articles ingested: {len(new_articles)}")

            triaged_articles = []
            article_count = len(new_articles)
            for count, article in enumerate(new_articles, 1):
                try:
                    result = triage_article(article, profile, tracked_client)
                    logger.info(
                        "Triage article %s/%s: relevance=%s, category=%s, title=%s",
                        count,
                        article_count,
                        result.relevance,
                        result.category,
                        article.title,
                    )
                    triaged_articles.append((article, result))
                    storage.mark_scored(article.url)
                except Exception:
                    logger.exception("Error triaging article '%s'", article.title)

            logger.info(f"Total articles triaged: {len(triaged_articles)}") 
            # Select articles for synthesis
            selected_articles = select_for_synthesis(triaged_articles, threshold=5, top_n_per_category=5)
            logger.info(f"Total articles selected for synthesis: {len(selected_articles)}")
            
            # Synthesize a digest from selected articles
            digest = synthesize(selected_articles,profile,tracked_client)
            logger.info(f"Total articles in digest: {len(digest)}")
            # Mark digested articles as digested in storage
            for digesteditem in digest:
                for url in digesteditem.article_urls:
                    storage.mark_digested(url)
                    digested_count += 1
            storage.finish_run(
                run_id,
                articles_fetched=len(new_articles),
                articles_scored=len(triaged_articles),
                articles_relevant=len(selected_articles),
                articles_digested= digested_count,
                total_input_tokens=tracked_client.total_input_tokens,
                total_output_tokens=tracked_client.total_output_tokens,
                estimated_cost_usd=estimate_cost(tracked_client.usage_by_model),
                status="completed",
            )
            return digest
        except Exception as e:
            logger.exception("Error during run: %s", e)
            storage.finish_run(
                run_id,
                status="failed",
                error_message=str(e),
                total_input_tokens=tracked_client.total_input_tokens,
                total_output_tokens=tracked_client.total_output_tokens,
                articles_fetched=len(new_articles),
                articles_scored=len(triaged_articles),
                articles_relevant=len(selected_articles),
                articles_digested= digested_count,
                estimated_cost_usd=estimate_cost(tracked_client.usage_by_model)
            )
            raise