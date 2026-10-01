from anthropic import Anthropic
from daily_assistant.adapters import AnthropicLLMClient, OpenAICompatibleAdapter
from daily_assistant.config import get_settings
from daily_assistant.telemetry import TrackedClient
from openai import OpenAI
from typing import TypedDict


class ModelConfig(TypedDict):
    triage: str
    synthesis: str


MODELS: dict[str, ModelConfig] = {
    "anthropic": {
        "triage": "claude-haiku-4-5-20251001",
        "synthesis": "claude-sonnet-5",
    },
    "local": {
        "triage": get_settings().local_model,
        "synthesis": get_settings().local_model,
    },
}


def build_client(
    local: bool = False,
) -> tuple[TrackedClient, ModelConfig]:
    if local:
        return (
            TrackedClient(
                OpenAICompatibleAdapter(
                    OpenAI(
                        base_url=get_settings().vllm_base_url,
                        api_key=get_settings().local_api_key,
                    )
                )
            ),
            MODELS["local"],
        )
    else:
        return (
            TrackedClient(
                AnthropicLLMClient(Anthropic(api_key=get_settings().anthropic_api_key))
            ),
            MODELS["anthropic"],
        )
