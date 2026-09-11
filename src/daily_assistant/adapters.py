import json
from typing import Any

from anthropic import Anthropic, Omit as AnthropicOmit
import anthropic
from anthropic.types import MessageParam, ToolChoiceToolParam, ToolParam
import openai
from daily_assistant.protocol import LLMConfigurationError, LLMProtocolError, LLMResponse, LLMClient, LLMTransientError
from openai import OpenAI, Omit as OpenAIOmit
from openai.types.chat import (
    ChatCompletionNamedToolChoiceParam,
    ChatCompletionToolParam,
)

_ANTHORPIC_TRANSIENT = (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError)
_ANTHORPIC_CONFIG = (anthropic.AuthenticationError, anthropic.PermissionDeniedError,
                     anthropic.NotFoundError, anthropic.BadRequestError)


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
        try:
            response = self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice=tool_choice,
                messages=messages,
                temperature=(temperature if temperature is not None else AnthropicOmit()),
            )
        except _ANTHORPIC_TRANSIENT as e:
            raise LLMTransientError(
                f"Transient error from Anthropic: {str(e)}",
                provider="anthropic",
                model=model,
            ) from e
        except _ANTHORPIC_CONFIG as e:
            raise LLMConfigurationError(
                f"Configuration error from Anthropic: {str(e)}",
                provider="anthropic",
                model=model,
            ) from e
        except anthropic.APIError as e:
            raise LLMProtocolError(
                f"Protocol error from Anthropic: {str(e)}",
                provider="anthropic",
                model=model,
            ) from e
        if response.stop_reason == "max_tokens":
            raise LLMProtocolError(
                "max_tokens are met before the model could finish its response. Consider increasing max_tokens.",
                provider="anthropic",
                model=model,
            )

        tool_use_block = None
        for block in response.content:
            if block.type == "tool_use":
                tool_use_block = block
                break

        if tool_use_block is None:
            raise LLMProtocolError(
                "Claude did not return a tool_use block",
                provider="anthropic",
                model=model,
    )
        return LLMResponse(
            tool_input=tool_use_block.input,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )



_OPENAI_TRANSIENT = (
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.InternalServerError,
)

_OPENAI_CONFIG = (
    openai.AuthenticationError,
    openai.PermissionDeniedError,
    openai.NotFoundError,
    openai.BadRequestError,
)

class OpenAICompatibleAdapter(LLMClient):
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

        tools: list[ChatCompletionToolParam] = [
            {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_description,
                    "parameters": tool_schema,
                    
                },
            }
        ]
        tool_choice: ChatCompletionNamedToolChoiceParam = {
            "type": "function",
            "function": {"name": tool_name},
        }
        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=max_tokens,
                tools=tools,
                tool_choice=tool_choice,
                temperature=temperature if temperature is not None else OpenAIOmit(),
            )
        except _OPENAI_TRANSIENT as e:
            raise LLMTransientError(
                f"Transient error from OpenAI: {str(e)}",
                provider="openai",
                model=model,
            ) from e
        except _OPENAI_CONFIG as e:
            raise LLMConfigurationError(
                f"Configuration error from OpenAI: {str(e)}",
                provider="openai",
                model=model,
            ) from e
        except openai.error.APIError as e:
            raise LLMProtocolError(
                f"Protocol error from OpenAI: {str(e)}",
                provider="openai",
                model=model,
            ) from e

        tool_calls = response.choices[0].message.tool_calls

        if tool_calls is None:
            raise LLMProtocolError(
                "OpenAI did not return a tool_calls item",
                provider="openai",
                model=model,
            )

        tool_call = next(
            (item for item in tool_calls if item.type == "function"),
            None,
        )

        choice = response.choices[0]
        if choice.finish_reason == "length":
            raise LLMProtocolError(
                "OpenAI API response was incomplete. Consider increasing max_tokens.",
                provider="openai",
                model=model,
            )
            
        if tool_call is None:
            raise LLMProtocolError("OpenAI did not return a function_call item",provider="openai",model=model)

        function = tool_call.function
        if function is None:
            raise LLMProtocolError("OpenAI function call had no function payload",provider="openai",model=model)
        tool_input = json.loads(function.arguments)
        if response.usage is None:
            raise ValueError("OpenAI response did not include usage")

        return LLMResponse(
            tool_input=tool_input,
            model=response.model,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )
