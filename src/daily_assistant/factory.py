from anthropic import Anthropic
from daily_assistant.adapters import AnthropicLLMClient, OpenAICompatibleAdapter
from daily_assistant.config import get_settings
from daily_assistant.telemetry import TrackedClient
from openai import OpenAI
from typing import TypedDict


class ModelConfig(TypedDict):
    triage: str
    synthesis: str


def build_client(
    local: bool = False,
) -> tuple[TrackedClient, ModelConfig]:
    settings = get_settings()

    if local:
        if settings.local_model is None:
            raise ValueError("Local model must be configured")
        if settings.vllm_base_url is None:
            raise ValueError("vLLM base URL must be configured")
        if settings.local_api_key is None:
            raise ValueError("Local API key must be configured")
        models: ModelConfig = {
            "triage": settings.local_model,
            "synthesis": settings.local_model,
        }
        client = TrackedClient(
            OpenAICompatibleAdapter(
                OpenAI(
                    base_url=settings.vllm_base_url,
                    api_key=settings.local_api_key,
                )
            )
        )
        return client, models

    models = {
        "triage": "claude-haiku-4-5-20251001",
        "synthesis": "claude-sonnet-5",
    }
    if settings.anthropic_api_key is None:
        raise ValueError("Anthropic API key must be configured")
    client = TrackedClient(
        AnthropicLLMClient(Anthropic(api_key=settings.anthropic_api_key))
    )
    return client, models
