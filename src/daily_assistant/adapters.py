import json
from typing import Any

from anthropic import Anthropic, Omit as AnthropicOmit
from anthropic.types import MessageParam, ToolChoiceToolParam, ToolParam
from daily_assistant.protocol import LLMResponse, LLMClient
from openai import OpenAI, Omit as OpenAIOmit
from openai.types.responses import FunctionToolParam, ToolChoiceFunctionParam

class AnthropicLLMClient(LLMClient):
    def __init__(self, client: Anthropic):
        self._client = client

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
        tools: list[ToolParam] = [
            {
                "name": tool_name,
                "description": tool_description,
                "input_schema": tool_schema,
            }
        ]
        tool_choice: ToolChoiceToolParam = {"type": "tool", "name": tool_name}
        messages: list[MessageParam] = [{"role": "user", "content": prompt}]

        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice=tool_choice,
            messages=messages,
            temperature=(
                temperature if temperature is not None else AnthropicOmit()
            ),
        )
        if response.stop_reason == "max_tokens":
            raise ValueError(
                "max_tokens are met before the model could finish its response. Consider increasing max_tokens."
            )

        tool_use_block = None
        for block in response.content:
            if block.type == "tool_use":
                tool_use_block = block
                break

        if tool_use_block is None:
            raise ValueError("Claude did not return a tool_use block")
        return LLMResponse(
            tool_input=tool_use_block.input,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

class OpenAIAdapter(LLMClient):
    def __init__(self, client: OpenAI):
        self._client = client

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

        tools: list[FunctionToolParam] = [
            {
                "type": "function",
                "name": tool_name,
                "description": tool_description,
                "parameters": tool_schema,
                "strict": True,
            }
        ]
        tool_choice: ToolChoiceFunctionParam = {
            "type": "function",
            "name": tool_name,
        }

        response = self._client.responses.create(
            model=model,
            input=prompt,
            max_output_tokens=max_tokens,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature if temperature is not None else OpenAIOmit(),
        )

        tool_call = next(
            (item for item in response.output if item.type == "function_call"),
            None,
        )
        if tool_call is None:
            raise ValueError("OpenAI did not return a function_call item")
        if response.status == "error":
            raise ValueError(f"OpenAI API error: {response.error_message}")
        if response.status == "incomplete":
            raise ValueError(
                "OpenAI API response was incomplete. Consider increasing max_tokens."
            )
        tool_input = json.loads(tool_call.arguments)
        if response.usage is None:
            raise ValueError("OpenAI response did not include usage")

        return LLMResponse(
            tool_input=tool_input,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        