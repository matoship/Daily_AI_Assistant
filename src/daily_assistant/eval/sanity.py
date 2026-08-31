from pathlib import Path
from yaml import safe_load
from daily_assistant.models import TriageResult,Fixture
from daily_assistant.triage import triage_article
import logging
from daily_assistant.profile import load_profile
from anthropic import Anthropic
from daily_assistant.telemetry import TrackedClient
from daily_assistant.config import get_settings
from daily_assistant.telemetry import estimate_cost
from daily_assistant.adapters import AnthropicLLMClient
logger = logging.getLogger(__name__)

def _resolve_path(path: str | Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = (Path(__file__).resolve().parents[3] / p).resolve()
    return p

def load_fixtures(path:str | Path="src/daily_assistant/eval/sanity_fixtures.yaml") -> list[Fixture]:
    with open(_resolve_path(path), "r", encoding="utf-8") as f:
        data = f.read()
        data = safe_load(data)
        data = data.get("fixtures", [])
        fixtures = []
        for fixture in data:
            fixture = Fixture(**fixture)
            fixtures.append(fixture)
        
    return fixtures

def check_fixture(fixture: Fixture, result: TriageResult) -> bool:
    """Judge one fixture's actual TriageResult against its expected min/max_relevance."""
    expected = fixture.expected

    min_relevance = expected.min_relevance
    max_relevance = expected.max_relevance

    if min_relevance is not None and result.relevance < min_relevance:
        return False
    if max_relevance is not None and result.relevance > max_relevance:
        return False
    return True

def run_sanity(fixtures: list[Fixture], profile:dict, client) -> list[dict]:
    """For each fixture: build an Article, call the real triage_article(), judge it,
    return a list of per-fixture results (id, passed, actual relevance, article title)
    for reporting."""

    results = []
    for fixture in fixtures:
        logger.info(f"Running sanity check for fixture ID: {fixture.id}")
        article = fixture.article
        triage_result = triage_article(article, profile, client)
        passed = check_fixture(fixture, triage_result)
        results.append({
            "id": fixture.id,
            "passed": passed,
            "actual_relevance": triage_result.relevance,
            "article_title": article.title
        })
    return results


def summarize_results(results: list[dict]) -> dict[str, int]:
    """Return totals for passed, failed, and total fixtures."""
    total = len(results)
    passed = sum(1 for result in results if result["passed"])
    failed = total - passed
    return {"total": total, "passed": passed, "failed": failed}


def main(path: str | Path = "src/daily_assistant/eval/sanity_fixtures.yaml") -> int:


    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING) 
    fixtures: list[Fixture] = load_fixtures(path)
    profile = load_profile()
    tracked_client = TrackedClient(Anthropic(api_key=get_settings().anthropic_api_key))
    llm = AnthropicLLMClient(tracked_client)
    results = run_sanity(fixtures, profile, llm)
    failed = [result for result in results if not result["passed"]]
    summary = summarize_results(results)
    for result in results:
        logger.info(
            f"Fixture ID: {result['id']}, Passed: {result['passed']}, "
            f"Actual Relevance: {result['actual_relevance']}, Article Title: {result['article_title']}"
        )
    logger.info(
        "Sanity summary: %s passed, %s failed, %s total",
        summary["passed"],
        summary["failed"],
        summary["total"],
    )
    logger.info("Sanity run cost: $%.4f", estimate_cost(tracked_client.usage_by_model))

    if failed:
        logger.error(f"Sanity check failed: {len(failed)} fixture(s) did not meet their thresholds.")
        return 1
    return 0



if __name__ == "__main__":
    raise SystemExit(main())

