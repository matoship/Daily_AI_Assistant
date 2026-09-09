from types import SimpleNamespace
import json
import httpx
import pytest
from anthropic import Omit as AnthropicOmit
from openai import Omit as OpenAIOmit, OpenAI

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


class FakeCompletions:
    def __init__(self, response):
        self.completions = FakeCompletionResource(response)


class FakeCompletionResource:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeOpenAIClient:
    def __init__(self, response):
        self.chat = FakeCompletions(response)


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
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    tool_calls=[
                        SimpleNamespace(
                            function=SimpleNamespace(
                                arguments='{"city": "Adelaide", "limit": 3}'
                            ),
                            type="function",
                        )
                    ]
                ),
                finish_reason="tool_calls",
            )
        ],
        model="gpt-5-mini",
        usage=SimpleNamespace(prompt_tokens=12, completion_tokens=34),
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

    assert len(client.chat.completions.calls) == 1
    request = client.chat.completions.calls[0]
    assert request["model"] == "gpt-5-mini"
    assert request["messages"] == [
        {"role": "user", "content": "Find local jobs in Adelaide."}
    ]
    assert request["max_completion_tokens"] == 256
    assert request["tools"] == [
        {
            "type": "function",
            "function": {
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
            },
        }
    ]
    assert request["tool_choice"] == {
        "type": "function",
        "function": {"name": "search_jobs"},
    }
    assert request["temperature"] == 0.2

    assert result == LLMResponse(
        tool_input={"city": "Adelaide", "limit": 3},
        model="gpt-5-mini",
        input_tokens=12,
        output_tokens=34,
    )


def test_openai_create_omits_temperature_when_not_provided():

    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    tool_calls=[
                        SimpleNamespace(
                            type="function",
                            function=SimpleNamespace(arguments='{"query": "AI eng'),
                        )
                    ]
                ),
                finish_reason="tool_calls",
            )
        ],
        model="gpt-5-mini",
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2),
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

    request = client.chat.completions.calls[0]
    assert isinstance(request["temperature"], OpenAIOmit)


def test_openai_create_raises_when_response_is_incomplete():
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    tool_calls=[SimpleNamespace(type="function", arguments={})]
                ),
                finish_reason="length",
            )
        ],
        model="gpt-5-mini",
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
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(tool_calls=[]),
                finish_reason="strop",
            )
        ],
        model="gpt-5-mini",
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


def mock_openai(request: httpx.Request) -> httpx.Response:
    assert request.method == "POST"
    assert request.url.path == "/v1/chat/completions"

    body = json.loads(request.content)

    assert body["model"] == "gpt-5-mini"

    return httpx.Response(
        status_code=200,
        json={
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "model": "gpt-5-mini",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_test",
                                "type": "function",
                                "function": {
                                    "name": "search_jobs",
                                    "arguments": ('{"city": "Adelaide", "limit": 3}'),
                                },
                            }
                        ],
                    },
                }
            ],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 34,
                "total_tokens": 46,
            },
        },
    )


def test_openai_adapter():
    transport = httpx.MockTransport(mock_openai)
    http_client = httpx.Client(transport=transport)

    client = OpenAI(
        api_key="test-key",
        http_client=http_client,
    )

    adapter = OpenAIAdapter(client)

    result = adapter.create(
        model="gpt-5-mini",
        max_tokens=256,
        prompt="Find local jobs in Adelaide.",
        tool_name="search_jobs",
        tool_description="Search for jobs.",
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
    print(result)
    assert result.tool_input == {
        "city": "Adelaide",
        "limit": 3,
    }
