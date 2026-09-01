from daily_assistant.eval.report import compare_changes, format_report


def test_format_report_renders_table_like_summary():
    confusion = {
        "overall": {"tp": 12, "fp": 9, "fn": 3, "tn": 26},
        "immigration": {"tp": 1, "fp": 8, "fn": 1, "tn": 13},
        "edge_case": {"tp": 0, "fp": 0, "fn": 1, "tn": 5},
        "other": {"tp": 0, "fp": 1, "fn": 0, "tn": 9}
    }
    metrics_result = {
        "overall": {"precision": 0.5714285714, "recall": 0.8, "f1": 0.6666666667},
        "immigration": {"precision": 0.1111111111, "recall": 0.5, "f1": 0.1818181818},
        "edge_case": {"precision": 0, "recall": 0.0, "f1": 0.0},
        "other": {"precision": 0, "recall": 0.0, "f1": 0.0}
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


def test_compare_changes_renders_before_after_delta_table():
    confusion = {
        "overall": {"tp": 12, "fp": 9, "fn": 3, "tn": 26},
        "overall_live": {"tp": 14, "fp": 7, "fn": 2, "tn": 28},
        "immigration": {"tp": 1, "fp": 8, "fn": 1, "tn": 13},
        "immigration_live": {"tp": 4, "fp": 3, "fn": 1, "tn": 15},
    }
    metrics_result = {
        "overall": {"precision": 0.57, "recall": 0.80, "f1": 0.67},
        "overall_live": {"precision": 0.78, "recall": 0.85, "f1": 0.81},
        "immigration": {"precision": 0.11, "recall": 0.50, "f1": 0.18},
        "immigration_live": {"precision": 0.64, "recall": 0.70, "f1": 0.67},
    }

    report = compare_changes(confusion, metrics_result)

    assert "subgroup" in report
    assert "TP" in report
    assert "FP" in report
    assert "FN" in report
    assert "TN" in report
    assert "P(before)" in report
    assert "P(after)" in report
    assert "ΔP" in report
    assert "Overall" in report
    assert "Immigration" in report
    assert "+0.21" in report
    assert "+0.53" in report

