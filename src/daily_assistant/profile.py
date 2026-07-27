from yaml import safe_load

def load_profile(path: str = "src/daily_assistant/profile.yaml") -> dict:
    with open(path, "r") as f:
        return safe_load(f)
    
def load_sources(path: str = "src/daily_assistant/source.yaml") -> list[dict]:
    with open(path, "r") as f:
        return safe_load(f).get("sources", [])
    
def category_options(profile: dict) -> list[str]:
    interests = profile.get("topics", {}).keys()
    return list(interests)