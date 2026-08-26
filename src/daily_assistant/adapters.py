from daily_assistant.protocol import LLMClient, LLMResponse
from anthropic import Anthropic
from typing import Any

class AnthropicLLMClient():
    def __init__(self, client:Anthropic):
        self._client = client

    def create(self,*,model:str, 
               max_tokens:int,
               prompt:str, 
               tool_name:str,
               tool_description:str,
               tool_schema:dict[str, Any], 
               temperature: float | None = None) -> LLMResponse:
        tools = [{"name":tool_name, 
                "description": tool_description,
                "input_schema":tool_schema
                }]
        tool_choice = {"type":"tool","name":tool_name}
        messages=[{"role":"user","content":prompt}]

        request_kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "tools": tools,
            "tool_choice": tool_choice,
            "messages": messages,
        }
        if temperature is not None:
            request_kwargs["temperature"] = temperature

        response= self._client.messages.create(**request_kwargs)
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
            truncated=response.stop_reason == "max_tokens",
        )