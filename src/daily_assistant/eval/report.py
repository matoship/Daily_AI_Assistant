import hashlib
import logging
from pathlib import Path
import argparse
from daily_assistant.telemetry import estimate_cost
from yaml import safe_load
from daily_assistant.factory import build_client
from daily_assistant.models import GoldLabel
from daily_assistant.triage import triage_article
from daily_assistant.profile import load_profile
import json
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _resolve_path(path: str | Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = (Path(__file__).resolve().parents[3] / p).resolve()
    return p


def load_golden_set(
    path: str | Path = "src/daily_assistant/eval/golden_set.yaml",
) -> list[GoldLabel]:
    with open(_resolve_path(path), "r", encoding="utf-8") as f:
        data = f.read()
        data = safe_load(data)
        data = data.get("labels", [])
        golden_labels = []
        for goldlabel in data:
            goldlabel = GoldLabel(**goldlabel)
            golden_labels.append(goldlabel)
    return golden_labels


def calculate_confusion(
    rows: list[tuple[GoldLabel, int, str]], gold_t=5, model_t=5
) -> dict:  # tp/fp/fn/tn — pure
    # true postive (tp): gold >= gold_t and model >= model_t
    # false positive (fp): gold < gold_t and model >= model_t
    # false negative (fn): gold >= gold_t and model < model_t
    # true negative (tn): gold < gold_t and model < model_t
    tp = fp = fn = tn = 0
    for goldlabel, model_relevance, _model_category in rows:
        if goldlabel.gold_relevance >= gold_t and model_relevance >= model_t:
            tp += 1
        elif goldlabel.gold_relevance < gold_t and model_relevance >= model_t:
            fp += 1
        elif goldlabel.gold_relevance >= gold_t and model_relevance < model_t:
            fn += 1
        else:
            tn += 1
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def metrics(conf) -> dict:  # precision/recall/F1 — pure
    tp = conf["tp"]
    fp = conf["fp"]
    fn = conf["fn"]
    _tn = conf["tn"]
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0
    )
    return {"precision": precision, "recall": recall, "f1": f1}


def group_by_category(
    rows: list[tuple[GoldLabel, int, str]],
) -> dict[str, list[tuple[GoldLabel, int, str]]]:
    grouped: dict[str, list[tuple[GoldLabel, int, str]]] = {}
    for row in rows:
        category = row[0].gold_category
        if category not in grouped:
            grouped[category] = []
        grouped[category].append(row)
    return grouped


def calculate_confusion_and_metrics(
    rows: list[tuple[GoldLabel, int, str]], gold_t=5, model_t=5
) -> tuple[dict, dict]:
    confusion = calculate_confusion(rows, gold_t, model_t)
    metrics_result = metrics(confusion)
    return confusion, metrics_result


def evaluate_offline(
    gold,
) -> list[tuple[GoldLabel, int, str]]:  # uses frozen scores, free
    rows = []
    for goldlabel in gold:
        rows.append((goldlabel, goldlabel.model_relevance, goldlabel.model_category))
    return rows


def evaluate_live(
    gold, profile, client
) -> list[tuple[GoldLabel, int, str]]:  # re-runs triage
    rows = []
    for goldlabel in gold:
        triaged = triage_article(goldlabel.article, profile, client)
        rows.append((goldlabel, triaged.relevance, triaged.category))
    return rows


def format_report(confusion, metrics_result) -> str:  # overall + subgroup breakdown
    def format_metric(value: float | None, *, fallback: str = "n/a") -> str:
        return fallback if value is None else f"{value:.2f}"

    header = f"{'subgroup':<24} {'TP':>4} {'FP':>4} {'FN':>4} {'TN':>4} {'P':>6} {'R':>6} {'F1':>6}"
    lines = [header, "-" * len(header)]

    for category, conf in confusion.items():
        label = category.replace("_", " ").title()
        m = metrics_result.get(category)
        if m is None:
            continue

        tp = conf["tp"]
        fp = conf["fp"]
        fn = conf["fn"]
        tn = conf["tn"]

        precision = None if tp + fp == 0 else m["precision"]
        recall = None if tp + fn == 0 else m["recall"]
        f1 = None if tp + fp == 0 or tp + fn == 0 else m["f1"]

        row = (
            f"{label:<24} {tp:>4} {fp:>4} {fn:>4} {tn:>4} "
            f"{format_metric(precision):>6} {format_metric(recall):>6} {format_metric(f1):>6}"
        )
        lines.append(row)

    return "\n".join(lines)


def compare_changes(
    rows: list[tuple[GoldLabel, int, str]],
    live_rows: list[tuple[GoldLabel, int, str]],
    gold_t: int = 5,
    model_t: int = 5,
) -> str:
    """Render article-level flips followed by live metrics for every subgroup."""
    if len(rows) != len(live_rows):
        raise ValueError(
            "Offline and live evaluations must contain the same number of rows"
        )

    header = (
        f"{'subgroup':<24} "
        f"{'FN->TP':>7} {'FP->TN':>7} "
        f"{'TP->FN':>7} {'TN->FP':>7} {'unchanged':>9} {'total':>6}"
    )
    lines = [header, "-" * len(header)]

    paired_rows = list(zip(rows, live_rows))
    subgroups = {"overall": paired_rows}
    subgroups["sufficient"] = [
        pair for pair in paired_rows if not pair[0][0].input_insufficient
    ]
    for category in dict.fromkeys(row[0].gold_category for row in rows):
        category_rows = [
            pair for pair in paired_rows if pair[0][0].gold_category == category
        ]
        subgroups[category] = category_rows
        subgroups[f"{category}_sufficient"] = [
            pair for pair in category_rows if not pair[0][0].input_insufficient
        ]

    for category, pairs in subgroups.items():
        flips = {"fn_tp": 0, "fp_tn": 0, "tp_fn": 0, "tn_fp": 0}
        unchanged = 0
        for (goldlabel, before_score, _), (live_goldlabel, after_score, _) in pairs:
            if goldlabel != live_goldlabel:
                raise ValueError("Offline and live evaluation rows are not aligned")

            gold_positive = goldlabel.gold_relevance >= gold_t
            before_positive = before_score >= model_t
            after_positive = after_score >= model_t
            if before_positive == after_positive:
                unchanged += 1
            elif gold_positive and not before_positive:
                flips["fn_tp"] += 1
            elif not gold_positive and before_positive:
                flips["fp_tn"] += 1
            elif gold_positive:
                flips["tp_fn"] += 1
            else:
                flips["tn_fp"] += 1

        label = category.replace("_", " ").title()
        row = (
            f"{label:<24} "
            f"{flips['fn_tp']:>7} {flips['fp_tn']:>7} "
            f"{flips['tp_fn']:>7} {flips['tn_fp']:>7} "
            f"{unchanged:>9} {len(pairs):>6}"
        )
        lines.append(row)

    live_confusion = {}
    live_metrics = {}
    live_subgroups = {
        "overall": live_rows,
        "sufficient": [row for row in live_rows if not row[0].input_insufficient],
    }
    for category in dict.fromkeys(row[0].gold_category for row in live_rows):
        live_category_rows = [row for row in live_rows if row[0].gold_category == category]
        live_subgroups[category] = live_category_rows
        live_subgroups[f"{category}_sufficient"] = [
            row for row in live_category_rows if not row[0].input_insufficient
        ]

    for category, subgroup_rows in live_subgroups.items():
        live_confusion[category], live_metrics[category] = (
            calculate_confusion_and_metrics(subgroup_rows, gold_t, model_t)
        )

    flip_table = "\n".join(lines)
    metrics_table = format_report(live_confusion, live_metrics)
    return f"Classification flips\n{flip_table}\n\nLive evaluation metrics\n{metrics_table}"


def write_report_to_file(
    report: str,
    *,
    profile: dict[str, Any],
    client_usage: dict[str, dict[str, int]],
    live_rows: list[tuple[GoldLabel, int, str]],
    path: str | Path = "src/daily_assistant/eval/history.jsonl",
    metrics_result: dict[str, dict[str, float]] | None = None,
) -> None:
    # Stable representation: identical profiles produce identical hashes
    canonical_profile = json.dumps(
        profile,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    profile_hash = hashlib.sha256(canonical_profile.encode("utf-8")).hexdigest()
    cost_estimate = estimate_cost(client_usage)
    model_id = list(client_usage.keys())
    logger.info(f"Estimated cost of live evaluation: ${cost_estimate:.4f}")

    serializable_live_rows = [
        {
            "article_url": goldlabel.article.url,
            "gold_relevance": goldlabel.gold_relevance,
            "gold_category": goldlabel.gold_category,
            "live_relevance": live_relevance,
            "live_category": live_category,
        }
        for goldlabel, live_relevance, live_category in live_rows
    ]

    record = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "profile_hash": profile_hash,
        "model_id": model_id,
        "report": report,
        "cost_estimate": cost_estimate,
        "live_rows": serializable_live_rows,
        "metrics_result": metrics_result,
    }

    resolved_path = _resolve_path(path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    with resolved_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="A script with a --live flag.")
    parser.add_argument(
        "-l", "--live", action="store_true", help="Enable live evaluation mode"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    golden_set: list[GoldLabel] = load_golden_set()
    rows = evaluate_offline(golden_set)
    rows_by_category = group_by_category(rows)
    sufficient_rows = [r for r in rows if not r[0].input_insufficient]
    sufficient_rows_by_category = group_by_category(sufficient_rows)
    confusion = {}
    metrics_result = {}

    confusion["overall"], metrics_result["overall"] = calculate_confusion_and_metrics(
        rows
    )
    confusion["sufficient"], metrics_result["sufficient"] = (
        calculate_confusion_and_metrics(sufficient_rows)
    )
    for category, cat_rows in rows_by_category.items():
        confusion[category], metrics_result[category] = calculate_confusion_and_metrics(
            cat_rows
        )

    for category, cat_rows in sufficient_rows_by_category.items():
        (
            confusion[f"{category}_sufficient"],
            metrics_result[f"{category}_sufficient"],
        ) = calculate_confusion_and_metrics(cat_rows)

    if args.live:
        # Evaluate live triage results
        logger.info(
            "Running live evaluation mode. This will re-run triage for each article in the golden set."
        )
        profile = load_profile()
        client = build_client()
        live_rows = evaluate_live(golden_set, profile, client)
        sufficient_rows_live = [r for r in live_rows if not r[0].input_insufficient]
        confusion["overall_live"], metrics_result["overall_live"] = (
            calculate_confusion_and_metrics(live_rows)
        )
        confusion["sufficient_live"], metrics_result["sufficient_live"] = (
            calculate_confusion_and_metrics(sufficient_rows_live)
        )
        for category, cat_rows in group_by_category(live_rows).items():
            confusion[f"{category}_live"], metrics_result[f"{category}_live"] = (
                calculate_confusion_and_metrics(cat_rows)
            )
        for category, cat_rows in group_by_category(sufficient_rows_live).items():
            (
                confusion[f"{category}_sufficient_live"],
                metrics_result[f"{category}_sufficient_live"],
            ) = calculate_confusion_and_metrics(cat_rows)
        report = compare_changes(rows, live_rows)
        write_report_to_file(
            report,
            profile=profile,
            client_usage=client.usage_by_model,
            live_rows=live_rows,
            metrics_result=metrics_result,
        )
    else:
        report = format_report(confusion, metrics_result)
    logger.info("\n%s", report)


if __name__ == "__main__":
    raise SystemExit(main())
