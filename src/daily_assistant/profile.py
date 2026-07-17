from yaml import safe_load

def load_profile(path: str = "profile.yaml") -> dict:
    with open(path, "r") as f:
        return safe_load(f)