from anthropic import Anthropic
from daily_assistant.adapters import AnthropicLLMClient
from daily_assistant.config import get_settings
from daily_assistant.telemetry import TrackedClient
    


def build_client() -> TrackedClient:      # TrackedClient satisfies LLMClient
    return TrackedClient(AnthropicLLMClient(Anthropic(api_key=get_settings().anthropic_api_key)))
