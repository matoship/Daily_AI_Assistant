from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class LLMResponse:
    tool_input: dict[str, Any]
    model: str
    input_tokens: int
    output_tokens: int



class LLMClient(Protocol):
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
    ) -> LLMResponse: ...
