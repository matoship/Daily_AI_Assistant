import os
from daily_assistant.telemetry import TrackedClient, estimate_cost
from daily_assistant.triage import triage_article
from daily_assistant.selection import select_for_synthesis
from daily_assistant.synthesize import synthesize
from daily_assistant.pipeline import ingest
from daily_assistant.profile import load_profile,load_sources
from daily_assistant.storage import Storage
from anthropic import Anthropic
from daily_assistant.config import get_settings
from daily_assistant.adapters import AnthropicLLMClient
from datetime import timedelta,datetime,timezone
from daily_assistant.render import render_digest_page, render_index
import webbrowser
from zoneinfo import ZoneInfo
import json
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

def main() -> None:
    digest = run()
    today = datetime.now(ZoneInfo("Australia/Adelaide")).strftime("%Y-%m-%d")

    output_dir = Path(__file__).resolve().parents[2] / "docs"
    output_dir.mkdir(exist_ok=True, parents=True)

    sidecar_path = output_dir / f".digest_{today}.json"
    existing_items = json.loads(sidecar_path.read_text()) if sidecar_path.exists() else []
    all_items = existing_items + [item.model_dump() for item in digest]
    sidecar_path.write_text(json.dumps(all_items))

    rendered_digest = render_digest_page(all_items, today)
    output_path = output_dir / f"digest_{today}.html"
    output_path.write_text(rendered_digest, encoding="utf-8")

    dates = sorted(
    (p.stem.removeprefix("digest_") for p in output_dir.glob("digest_*.html")),
    reverse=True,
    )
    rendered_index = render_index(dates)
    index_path = output_dir / "index.html" 

    index_path.write_text(rendered_index, encoding="utf-8")
    if not os.environ.get("CI"):
        webbrowser.open_new_tab(index_path.as_uri()) 

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
    llm = AnthropicLLMClient(tracked_client)
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
                    result = triage_article(article, profile, llm)
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
                    storage.store_triage_log(
                        url=article.url,
                        source=article.source,
                        title=article.title,
                        summary=article.summary,
                        relevance=result.relevance,
                        category=result.category,
                        reason=result.reason
                    )
                except Exception:
                    logger.exception("Error triaging article '%s'", article.title)

            logger.info(f"Total articles triaged: {len(triaged_articles)}") 
            # Select articles for synthesis
            selected_articles = select_for_synthesis(triaged_articles, threshold=5, top_n_per_category=5)
            logger.info(f"Total articles selected for synthesis: {len(selected_articles)}")
            
            # Synthesize a digest from selected articles
            digest = synthesize(selected_articles,profile,llm)
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