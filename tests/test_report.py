import hashlib
import json

from daily_assistant.eval.report import (
    compare_changes,
    format_report,
    write_report_to_file,
)
from daily_assistant.models import Article, GoldLabel


def test_format_report_renders_table_like_summary():
    confusion = {
        "overall": {"tp": 12, "fp": 9, "fn": 3, "tn": 26},
        "immigration": {"tp": 1, "fp": 8, "fn": 1, "tn": 13},
        "edge_case": {"tp": 0, "fp": 0, "fn": 1, "tn": 5},
        "other": {"tp": 0, "fp": 1, "fn": 0, "tn": 9},
    }
    metrics_result = {
        "overall": {"precision": 0.5714285714, "recall": 0.8, "f1": 0.6666666667},
        "immigration": {"precision": 0.1111111111, "recall": 0.5, "f1": 0.1818181818},
        "edge_case": {"precision": 0, "recall": 0.0, "f1": 0.0},
        "other": {"precision": 0, "recall": 0.0, "f1": 0.0},
    }

    report = format_report(confusion, metrics_result)

    assert "subgroup" in report
    assert "TP" in report
    assert "FP" in report
    assert "overall" in report.lower()
    assert "immigration" in report.lower()
    assert "0.57" in report
    assert "0.11" in report
    assert "n/a" in report
    assert "0.00" in report


def test_compare_changes_renders_classification_flip_table():
    def label(relevance, *, insufficient=False):
        return GoldLabel(
            article=Article(
                title="Test", summary="Test", url="https://example.com", source="Test"
            ),
            gold_relevance=relevance,
            gold_category="immigration",
            input_insufficient=insufficient,
            model_relevance=0,
            model_category="immigration",
        )

    labels = [label(8), label(2), label(9), label(1), label(7, insufficient=True)]
    rows = [
        (labels[0], 3, ""),
        (labels[1], 8, ""),
        (labels[2], 7, ""),
        (labels[3], 2, ""),
        (labels[4], 8, ""),
    ]
    live_rows = [
        (labels[0], 8, ""),
        (labels[1], 2, ""),
        (labels[2], 3, ""),
        (labels[3], 8, ""),
        (labels[4], 9, ""),
    ]

    report = compare_changes(rows, live_rows)

    assert "subgroup" in report
    assert "FN->TP" in report
    assert "FP->TN" in report
    assert "TP->FN" in report
    assert "TN->FP" in report
    assert "unchanged" in report
    assert "Overall" in report
    assert "Immigration" in report
    assert (
        "Overall                        1       1       1       1         1      5"
        in report
    )
    assert (
        "Sufficient                     1       1       1       1         0      4"
        in report
    )
    assert "Live evaluation metrics" in report
    assert "subgroup                   TP   FP   FN   TN" in report
    assert "2    1    1    1   0.67   0.67   0.67" in report
    assert "Immigration Sufficient" in report


def test_write_report_to_file_creates_file_and_appends_jsonl(tmp_path):
    profile = {
        "topics": {"immigration": {"priority": "high"}},
        "location": "Australia",
    }
    goldlabel = GoldLabel(
        article=Article(
            title="Test article",
            summary="Test summary",
            url="https://example.com/article",
            source="Example",
        ),
        gold_relevance=8,
        gold_category="immigration",
        model_relevance=6,
        model_category="immigration",
    )
    live_rows = [(goldlabel, 9, "immigration")]
    client_usage = {
        "claude-haiku-4-5-20251001": {
            "input_tokens": 1_000_000,
            "output_tokens": 1_000_000,
        }
    }
    metrics_result = {"overall_live": {"precision": 1.0, "recall": 1.0, "f1": 1.0}}
    history_path = tmp_path / "history.jsonl"

    write_report_to_file(
        "First report",
        profile=profile,
        client_usage=client_usage,
        live_rows=live_rows,
        path=history_path,
        metrics_result=metrics_result,
    )
    write_report_to_file(
        "Second report",
        profile=profile,
        client_usage=client_usage,
        live_rows=live_rows,
        path=history_path,
        metrics_result=metrics_result,
    )

    records = [
        json.loads(line)
        for line in history_path.read_text(encoding="utf-8").splitlines()
    ]
    canonical_profile = json.dumps(
        profile, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    expected_hash = hashlib.sha256(canonical_profile.encode("utf-8")).hexdigest()

    assert len(records) == 2
    assert records[0]["report"] == "First report"
    assert records[1]["report"] == "Second report"
    assert records[0]["profile_hash"] == expected_hash
    assert records[0]["model_id"] == ["claude-haiku-4-5-20251001"]
    assert records[0]["cost_estimate"] == 6.0
    assert records[0]["metrics_result"] == metrics_result
    assert records[0]["created_at"]
    assert records[0]["live_rows"] == [
        {
            "article_url": "https://example.com/article",
            "gold_relevance": 8,
            "gold_category": "immigration",
            "live_relevance": 9,
            "live_category": "immigration",
        }
    ]
