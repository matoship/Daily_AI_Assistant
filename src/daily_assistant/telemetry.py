import logging
from typing import Any
from daily_assistant.protocol import LLMClient, LLMResponse

logger = logging.getLogger(__name__)

PRICING = {
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
    "claude-sonnet-5": {"input": 2.00, "output": 10.00},  # introductory rate, expires 2026-09-01
}

def estimate_cost(usage_by_model: dict[str, dict[str, int]]) -> float:
    total_cost = 0.0
    for model, usage in usage_by_model.items():
        if model in PRICING:
            input_cost = (usage["input_tokens"] / 1000000) * PRICING[model]["input"]
            output_cost = (usage["output_tokens"] / 1000000) * PRICING[model]["output"]
            total_cost += input_cost + output_cost
        else:
            logger.warning(f"Pricing for model {model} not found. Skipping cost estimation for this model.")
    return total_cost


class TrackedClient(LLMClient):
    def __init__(self, client):
        self.usage_by_model: dict[str, dict[str, int]] = {}
        self._client = client
    def record_usage(self, model: str, input_tokens: int, output_tokens: int) -> None:
        if model not in self.usage_by_model:
            self.usage_by_model[model] = {"input_tokens": 0, "output_tokens": 0}
        self.usage_by_model[model]["input_tokens"] += input_tokens
        self.usage_by_model[model]["output_tokens"] += output_tokens

    @property
    def total_input_tokens(self) -> int:
        return sum(usage["input_tokens"] for usage in self.usage_by_model.values())

    @property
    def total_output_tokens(self) -> int:
        return sum(usage["output_tokens"] for usage in self.usage_by_model.values())

    def create(self,*, model: str,
                max_tokens: int, 
                prompt: str,
                tool_name: str, 
                tool_description: str,
                tool_schema: dict[str, Any],
                temperature: float | None = None) -> LLMResponse:

        response = self._client.create(
            model=model,
            max_tokens=max_tokens,
            prompt=prompt,
            tool_name=tool_name,
            tool_description=tool_description,
            tool_schema=tool_schema,
            temperature=temperature
        )
        self.record_usage(
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens
        )
        return response
