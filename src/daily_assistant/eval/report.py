from daily_assistant.models import GoldLabel

def load_golden_set(path) -> list[GoldLabel]: ...


def confusion(pairs, gold_t=5, model_t=5) -> dict: ...     # tp/fp/fn/tn — pure

def metrics(conf) -> dict: ...                             # precision/recall/F1 — pure

def evaluate_offline(gold) -> list[tuple[GoldLabel, int, str]]: ...   # uses frozen scores, free

def evaluate_live(gold, profile, client) -> list[tuple[GoldLabel, int, str]]: ...  # re-runs triage

def format_report(rows) -> str: ...                        # overall + subgroup breakdown