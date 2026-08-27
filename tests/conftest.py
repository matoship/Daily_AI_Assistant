from collections.abc import Callable
from typing import Any

import pytest

from daily_assistant.protocol import LLMClient, LLMResponse


class FakeLLMClient:
    def __init__(self, response: LLMResponse):
        self.response = response

    def create(
        self,
        *,
        model: str,
        max_tokens: int,
        prompt: str,
        tool_name: str,
        tool_description: str,
        tool_schema: dict[str, Any],
        temperature: float | None = None,
    ) -> LLMResponse:
        return self.response


@pytest.fixture
def fake_llm_client() -> Callable[[LLMResponse], LLMClient]:
    return FakeLLMClient