from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }
    anthropic_api_key: str

# @lru_cache()
def get_settings() -> Settings:
    return Settings()

get_settings()  # Load settings at startup to ensure they are available
print(get_settings().anthropic_api_key)