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

class LLMError(Exception):
    """Base class for LLM-related errors."""
    def __init__(self, message: str, *, provider: str, model: str | None = None) -> None:         
        super().__init__(message)
        self.provider = provider
        self.model = model

class LLMTransientError(LLMError):
    """Indicates a transient error that may succeed if retried."""

class LLMConfigurationError(LLMError):
    """Indicates a configuration error that should be fixed before retrying."""

class LLMProtocolError(LLMError):
    """Indicates a protocol error in the interaction with the LLM."""

