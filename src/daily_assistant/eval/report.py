import logging
from pathlib import Path
import argparse
from yaml import safe_load
from daily_assistant.factory import build_client
from daily_assistant.models import GoldLabel
from daily_assistant.triage import triage_article
from daily_assistant.profile import load_profile

logger = logging.getLogger(__name__)

def _resolve_path(path: str | Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = (Path(__file__).resolve().parents[3] / p).resolve()
    return p

def load_golden_set( path:str | Path = "src/daily_assistant/eval/golden_set.yaml") -> list[GoldLabel]: 
    with open(_resolve_path(path), "r", encoding="utf-8") as f:
        data = f.read()
        data = safe_load(data)
        data = data.get("labels", [])
        golden_labels = []
        for goldlabel in data:
            goldlabel = GoldLabel(**goldlabel)
            golden_labels.append(goldlabel)
    return golden_labels

def calculate_confusion(rows: list[tuple[GoldLabel, int, str]], gold_t=5, model_t=5) -> dict:     # tp/fp/fn/tn — pure
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

def metrics(conf) -> dict:                             # precision/recall/F1 — pure
    tp = conf["tp"]
    fp = conf["fp"]
    fn = conf["fn"]
    _tn = conf["tn"]
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    return {"precision": precision, "recall": recall, "f1": f1}

def group_by_category(rows: list[tuple[GoldLabel, int, str]]) -> dict[str, list[tuple[GoldLabel, int, str]]]:
    grouped = {}
    for row in rows:
        category = row[0].gold_category
        if category not in grouped:
            grouped[category] = []
        grouped[category].append(row)
    return grouped

def calculate_confusion_and_metrics(rows: list[tuple[GoldLabel, int, str]], gold_t=5, model_t=5) -> tuple[dict, dict]:
    confusion = calculate_confusion(rows, gold_t, model_t)
    metrics_result = metrics(confusion)
    return confusion, metrics_result

def evaluate_offline(gold) -> list[tuple[GoldLabel, int, str]]:    # uses frozen scores, free
    rows =[]
    for goldlabel in gold:
        rows.append((goldlabel, goldlabel.model_relevance, goldlabel.model_category))
    return rows

def evaluate_live(gold, profile, client) -> list[tuple[GoldLabel, int, str]]:   # re-runs triage
    rows = []
    for goldlabel in gold:
        triaged = triage_article(goldlabel.article, profile, client)
        rows.append((goldlabel, triaged.relevance, triaged.category))
    return rows

def format_report(confusion, metrics_result) -> str:                        # overall + subgroup breakdown
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

def compare_changes(confusion, metrics_result) -> str:
    def format_metric(value: float | None, *, fallback: str = "n/a") -> str:
        return fallback if value is None else f"{value:.2f}"

    header = (
        f"{'subgroup':<24} "
        f"{'TP':>4} {'FP':>4} {'FN':>4} {'TN':>4} "
        f"{'P(before)':>10} {'P(after)':>10} {'ΔP':>8} "
        f"{'R(before)':>10} {'R(after)':>10} {'ΔR':>8} "
        f"{'F1(before)':>11} {'F1(after)':>11} {'ΔF1':>8}"
    )
    lines = [header, "-" * len(header)]

    for category, live_metrics in metrics_result.items():
        if not category.endswith("_live"):
            continue

        base_category = category[:-5]
        base_metrics = metrics_result.get(base_category)
        if not base_metrics:
            continue

        before_p = base_metrics["precision"]
        after_p = live_metrics["precision"]
        delta_p = after_p - before_p

        before_r = base_metrics["recall"]
        after_r = live_metrics["recall"]
        delta_r = after_r - before_r

        before_f1 = base_metrics["f1"]
        after_f1 = live_metrics["f1"]
        delta_f1 = after_f1 - before_f1

        base_confusion = confusion.get(base_category)
        live_confusion = confusion.get(category)
        if base_confusion is None or live_confusion is None:
            continue

        tp = live_confusion["tp"]
        fp = live_confusion["fp"]
        fn = live_confusion["fn"]
        tn = live_confusion["tn"]

        label = base_category.replace("_", " ").title()
        row = (
            f"{label:<24} "
            f"{tp:>4} {fp:>4} {fn:>4} {tn:>4} "
            f"{format_metric(before_p):>10} {format_metric(after_p):>10} {delta_p:>+8.2f} "
            f"{format_metric(before_r):>10} {format_metric(after_r):>10} {delta_r:>+8.2f} "
            f"{format_metric(before_f1):>11} {format_metric(after_f1):>11} {delta_f1:>+8.2f}"
        )
        lines.append(row)

    return "\n".join(lines)

def main(argv=None):
    parser = argparse.ArgumentParser(description="A script with a --live flag.")
    parser.add_argument('-l', '--live', action='store_true', help='Enable live evaluation mode')
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
    confusion={}
    metrics_result={}


    confusion["overall"], metrics_result["overall"] = calculate_confusion_and_metrics(rows)
    confusion["sufficient"], metrics_result["sufficient"] = calculate_confusion_and_metrics(sufficient_rows)
    for category, cat_rows in rows_by_category.items():
        confusion[category], metrics_result[category] = calculate_confusion_and_metrics(cat_rows)

    for category, cat_rows in sufficient_rows_by_category.items():
        confusion[f"{category}_sufficient"], metrics_result[f"{category}_sufficient"] = calculate_confusion_and_metrics(cat_rows)

    if args.live:
        # Evaluate live triage results
        logger.info("Running live evaluation mode. This will re-run triage for each article in the golden set.")
        profile = load_profile()
        live_rows = evaluate_live(golden_set, profile, client=build_client())
        confusion["overall_live"], metrics_result["overall_live"] = calculate_confusion_and_metrics(live_rows)
        for category, cat_rows in group_by_category(live_rows).items():
            confusion[f"{category}_live"], metrics_result[f"{category}_live"] = calculate_confusion_and_metrics(cat_rows)
        report = compare_changes(confusion,metrics_result)
    else:
        report = format_report(confusion,metrics_result)
    logger.info("\n%s", report)

if __name__ == "__main__":
    raise SystemExit(main())