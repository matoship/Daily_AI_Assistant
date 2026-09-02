from types import SimpleNamespace
import json

import pytest
from anthropic import Omit as AnthropicOmit
from openai import Omit as OpenAIOmit

from daily_assistant.adapters import AnthropicLLMClient, OpenAIAdapter
from daily_assistant.protocol import LLMResponse


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeAnthropicClient:
    def __init__(self, response):
        self.messages = FakeMessages(response)


class FakeResponses:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeOpenAIClient:
    def __init__(self, response):
        self.responses = FakeResponses(response)


def test_create_builds_tool_request_and_maps_response():
    response = SimpleNamespace(
        model="claude-3-5-haiku-20241022",
        stop_reason="tool_use",
        usage=SimpleNamespace(input_tokens=12, output_tokens=34),
        content=[
            SimpleNamespace(
                type="tool_use",
                input={"city": "Adelaide", "limit": 3},
            )
        ],
    )
    client = FakeAnthropicClient(response)
    adapter = AnthropicLLMClient(client)

    result = adapter.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=256,
        prompt="Find local jobs in Adelaide.",
        tool_name="search_jobs",
        tool_description="Search for jobs matching a location and limit.",
        tool_schema={
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["city"],
        },
        temperature=0.2,
    )

    assert len(client.messages.calls) == 1
    request = client.messages.calls[0]
    assert request["model"] == "claude-3-5-haiku-20241022"
    assert request["max_tokens"] == 256
    assert request["messages"] == [
        {"role": "user", "content": "Find local jobs in Adelaide."}
    ]
    assert request["tools"] == [
        {
            "name": "search_jobs",
            "description": "Search for jobs matching a location and limit.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["city"],
            },
        }
    ]
    assert request["tool_choice"] == {"type": "tool", "name": "search_jobs"}
    assert request["temperature"] == 0.2

    assert result == LLMResponse(
        tool_input={"city": "Adelaide", "limit": 3},
        model="claude-3-5-haiku-20241022",
        input_tokens=12,
        output_tokens=34,
    )


def test_create_omits_temperature_when_not_provided():
    response = SimpleNamespace(
        model="claude-3-5-haiku-20241022",
        stop_reason="tool_use",
        usage=SimpleNamespace(input_tokens=1, output_tokens=2),
        content=[SimpleNamespace(type="tool_use", input={"query": "AI engineer"})],
    )
    client = FakeAnthropicClient(response)
    adapter = AnthropicLLMClient(client)

    adapter.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=64,
        prompt="Find AI jobs.",
        tool_name="search",
        tool_description="Search for jobs.",
        tool_schema={"type": "object", "properties": {"query": {"type": "string"}}},
    )

    request = client.messages.calls[0]
    assert isinstance(request["temperature"], AnthropicOmit)


def test_create_raises_when_response_has_no_tool_use_block():
    response = SimpleNamespace(
        model="claude-3-5-haiku-20241022",
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=8, output_tokens=9),
        content=[
            SimpleNamespace(type="text", text="I cannot help with that."),
        ],
    )
    client = FakeAnthropicClient(response)
    adapter = AnthropicLLMClient(client)

    with pytest.raises(ValueError, match="Claude did not return a tool_use block"):
        adapter.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=32,
            prompt="Find jobs.",
            tool_name="search",
            tool_description="Search for jobs.",
            tool_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        )


def test_create_raises_when_response_is_truncated_by_max_tokens():
    response = SimpleNamespace(
        model="claude-3-5-haiku-20241022",
        stop_reason="max_tokens",
        usage=SimpleNamespace(input_tokens=8, output_tokens=9),
        content=[
            SimpleNamespace(type="text", text="answer was truncated"),
        ],
    )
    client = FakeAnthropicClient(response)
    adapter = AnthropicLLMClient(client)

    with pytest.raises(
        ValueError,
        match="max_tokens are met before the model could finish its response. Consider increasing max_tokens.",
    ):
        adapter.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=8,
            prompt="Find jobs.",
            tool_name="search",
            tool_description="Search for jobs.",
            tool_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        )


def test_openai_create_builds_tool_request_and_maps_response():
    response = SimpleNamespace(
        model="gpt-5-mini",
        status="completed",
        usage=SimpleNamespace(input_tokens=12, output_tokens=34),
        output=[
            SimpleNamespace(
                type="message",
                content=[SimpleNamespace(type="output_text", text="ignored")],
            ),
            SimpleNamespace(
                type="function_call",
                arguments='{"city": "Adelaide", "limit": 3}',
            ),
        ],
    )
    client = FakeOpenAIClient(response)
    adapter = OpenAIAdapter(client)

    result = adapter.create(
        model="gpt-5-mini",
        max_tokens=256,
        prompt="Find local jobs in Adelaide.",
        tool_name="search_jobs",
        tool_description="Search for jobs matching a location and limit.",
        tool_schema={
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["city"],
        },
        temperature=0.2,
    )

    assert len(client.responses.calls) == 1
    request = client.responses.calls[0]
    assert request["model"] == "gpt-5-mini"
    assert request["input"] == "Find local jobs in Adelaide."
    assert request["max_output_tokens"] == 256
    assert request["tools"] == [
        {
            "type": "function",
            "name": "search_jobs",
            "description": "Search for jobs matching a location and limit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["city"],
            },
            "strict": True,
        }
    ]
    assert request["tool_choice"] == {"type": "function", "name": "search_jobs"}
    assert request["temperature"] == 0.2

    assert result == LLMResponse(
        tool_input={"city": "Adelaide", "limit": 3},
        model="gpt-5-mini",
        input_tokens=12,
        output_tokens=34,
    )


def test_openai_create_omits_temperature_when_not_provided():
    response = SimpleNamespace(
        model="gpt-5-mini",
        status="completed",
        usage=SimpleNamespace(input_tokens=1, output_tokens=2),
        output=[
            SimpleNamespace(
                type="function_call",
                arguments='{"query": "AI eng'
            )
        ],
    )
    client = FakeOpenAIClient(response)
    adapter = OpenAIAdapter(client)

    with pytest.raises(json.JSONDecodeError, match="Unterminated string"):
        adapter.create(
            model="gpt-5-mini",
            max_tokens=64,
            prompt="Find AI jobs.",
            tool_name="search",
            tool_description="Search for jobs.",
            tool_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        )

    request = client.responses.calls[0]
    assert isinstance(request["temperature"], OpenAIOmit)


def test_openai_create_raises_when_response_has_api_error():
    response = SimpleNamespace(
        status="error",
        error_message="rate limit exceeded",
        output=[SimpleNamespace(type="function_call", arguments="{}")],
    )
    client = FakeOpenAIClient(response)
    adapter = OpenAIAdapter(client)

    with pytest.raises(ValueError, match="OpenAI API error: rate limit exceeded"):
        adapter.create(
            model="gpt-5-mini",
            max_tokens=32,
            prompt="Find jobs.",
            tool_name="search",
            tool_description="Search for jobs.",
            tool_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        )


def test_openai_create_raises_when_response_is_incomplete():
    response = SimpleNamespace(
        status="incomplete",
        output=[SimpleNamespace(type="function_call", arguments="{}")],
    )
    client = FakeOpenAIClient(response)
    adapter = OpenAIAdapter(client)

    with pytest.raises(
        ValueError,
        match="OpenAI API response was incomplete. Consider increasing max_tokens.",
    ):
        adapter.create(
            model="gpt-5-mini",
            max_tokens=8,
            prompt="Find jobs.",
            tool_name="search",
            tool_description="Search for jobs.",
            tool_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        )


def test_openai_create_raises_when_response_has_no_function_call():
    response = SimpleNamespace(
        status="completed",
        output=[SimpleNamespace(type="message")],
    )
    client = FakeOpenAIClient(response)
    adapter = OpenAIAdapter(client)

    with pytest.raises(ValueError, match="OpenAI did not return a function_call item"):
        adapter.create(
            model="gpt-5-mini",
            max_tokens=32,
            prompt="Find jobs.",
            tool_name="search",
            tool_description="Search for jobs.",
            tool_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        )

