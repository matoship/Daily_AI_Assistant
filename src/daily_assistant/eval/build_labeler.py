"""Build a self-contained HTML labeler for the triage golden set.

Reads rows from `triage_logs`, takes a stratified sample (oversampling the
relevance band around the selection threshold, where agreement actually
decides precision/recall), inlines them into an HTML template, and writes a
single file you can open in a browser.

The labeler is deliberately *blind*: it hides the model's own score until
after each judgement is submitted, so the human labels stay independent
rather than anchoring on what triage already decided.

    uv run python -m daily_assistant.eval.build_labeler
"""

import json
import logging
import random
import sqlite3
from collections import defaultdict
from pathlib import Path

from daily_assistant.profile import category_options, load_profile

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = Path(__file__).resolve().parent / "labeler_template.html"
OUTPUT = Path(__file__).resolve().parent / "labeler.html"

# Articles scoring near the threshold are where a wrong call flips a
# precision/recall decision, so they are worth more of the labelling budget
# than obvious 1s and 10s.
THRESHOLD = 5
BOUNDARY = {4, 5, 6}
BOUNDARY_SHARE = 0.5


def load_rows(db_path: Path) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT url, source, title, summary, relevance, category, reason
            FROM triage_logs
            GROUP BY url
            ORDER BY created_at DESC
            """
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def stratified_sample(rows: list[dict], size: int, seed: int = 0) -> list[dict]:
    """Sample `size` rows, spending BOUNDARY_SHARE of the budget near the threshold."""
    rng = random.Random(seed)
    boundary = [r for r in rows if r["relevance"] in BOUNDARY]
    rest = [r for r in rows if r["relevance"] not in BOUNDARY]

    want_boundary = min(len(boundary), round(size * BOUNDARY_SHARE))
    picked = rng.sample(boundary, want_boundary)

    # Spread the remainder evenly across the other relevance scores so the set
    # is not dominated by whichever score happens to be most common.
    by_score = defaultdict(list)
    for r in rest:
        by_score[r["relevance"]].append(r)
    for bucket in by_score.values():
        rng.shuffle(bucket)

    while len(picked) < size and any(by_score.values()):
        for score in sorted(by_score):
            if len(picked) >= size:
                break
            if by_score[score]:
                picked.append(by_score[score].pop())

    rng.shuffle(picked)  # avoid labelling all the easy ones in a row
    return picked


def build(db_path: Path | None = None, size: int = 50, seed: int = 0) -> Path:
    db_path = db_path or REPO_ROOT / "seen.db"
    rows = load_rows(db_path)
    if not rows:
        raise SystemExit(f"No rows in triage_logs in {db_path} - run the pipeline first.")

    sample = stratified_sample(rows, size, seed)
    items = [
        {
            "url": r["url"],
            "source": r["source"],
            "title": r["title"],
            "summary": r["summary"],
            "model_relevance": r["relevance"],
            "model_category": r["category"],
            "model_reason": r["reason"],
        }
        for r in sample
    ]

    categories = category_options(load_profile()) + ["other"]

    html = TEMPLATE.read_text(encoding="utf-8")
    html = html.replace("/*__DATA__*/[]", json.dumps(items, ensure_ascii=False))
    html = html.replace(
        '/*__CATS__*/["engineering","immigration","other"]',
        json.dumps(categories, ensure_ascii=False),
    )
    OUTPUT.write_text(html, encoding="utf-8")

    dist = defaultdict(int)
    for it in items:
        dist[it["model_relevance"]] += 1
    logger.info("pool=%s sampled=%s", len(rows), len(items))
    logger.info("sample distribution by model relevance: %s", dict(sorted(dist.items())))
    return OUTPUT


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
    out = build()
    print(f"\nOpen this in a browser to start labelling:\n  {out}\n")


if __name__ == "__main__":
    main()
