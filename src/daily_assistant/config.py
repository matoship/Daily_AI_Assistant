from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }
    anthropic_api_key: str = Field(..., min_length=1)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
