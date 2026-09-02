from pathlib import Path
from yaml import safe_load


def _resolve_path(path: str | Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = (Path(__file__).resolve().parents[2] / p).resolve()
    return p


def load_profile(path: str | Path = "src/daily_assistant/profile.yaml") -> dict:
    with open(_resolve_path(path), "r", encoding="utf-8") as f:
        return safe_load(f)


def load_sources(path: str | Path = "src/daily_assistant/source.yaml") -> list[dict]:
    with open(_resolve_path(path), "r", encoding="utf-8") as f:
        data = safe_load(f) or {}
        return data.get("sources", [])


def category_options(profile: dict) -> list[str]:
    interests = profile.get("topics", {}).keys()
    return list(interests)
