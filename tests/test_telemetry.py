from types import SimpleNamespace

from daily_assistant.telemetry import TrackedClient, estimate_cost


def test_tracked_client():
    class MockUnderlyingClient:
        def create(
            self,
            *,
            model,
            max_tokens,
            prompt,
            tool_name,
            tool_description,
            tool_schema,
            temperature=None,
        ):
            return SimpleNamespace(
                model=model,
                input_tokens=1000,
                output_tokens=2000,
            )

    mock_client = MockUnderlyingClient()
    tracked_client = TrackedClient(mock_client)

    tracked_client.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        prompt="hello",
        tool_name="demo_tool",
        tool_description="demo",
        tool_schema={"type": "object", "properties": {}},
    )

    assert (
        tracked_client.usage_by_model["claude-haiku-4-5-20251001"]["input_tokens"]
        == 1000
    )
    assert (
        tracked_client.usage_by_model["claude-haiku-4-5-20251001"]["output_tokens"]
        == 2000
    )

    estimated_cost = estimate_cost(tracked_client.usage_by_model)
    expected_cost = 0.001 + 0.01
    assert estimated_cost == expected_cost


def test_token_counting_with_different_models():
    class MockUnderlyingClient:
        def create(
            self,
            *,
            model,
            max_tokens,
            prompt,
            tool_name,
            tool_description,
            tool_schema,
            temperature=None,
        ):
            if model == "claude-haiku-4-5-20251001":
                return SimpleNamespace(
                    model=model,
                    input_tokens=500,
                    output_tokens=1000,
                )
            elif model == "claude-sonnet-5":
                return SimpleNamespace(
                    model=model,
                    input_tokens=2000,
                    output_tokens=4000,
                )
            return SimpleNamespace(
                model=model,
                input_tokens=0,
                output_tokens=0,
            )

    mock_client = MockUnderlyingClient()
    tracked_client = TrackedClient(mock_client)

    tracked_client.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        prompt="hello",
        tool_name="demo_tool",
        tool_description="demo",
        tool_schema={"type": "object", "properties": {}},
    )
    tracked_client.create(
        model="claude-sonnet-5",
        max_tokens=200,
        prompt="hello",
        tool_name="demo_tool",
        tool_description="demo",
        tool_schema={"type": "object", "properties": {}},
    )

    assert (
        tracked_client.usage_by_model["claude-haiku-4-5-20251001"]["input_tokens"]
        == 500
    )
    assert (
        tracked_client.usage_by_model["claude-haiku-4-5-20251001"]["output_tokens"]
        == 1000
    )
    assert tracked_client.usage_by_model["claude-sonnet-5"]["input_tokens"] == 2000
    assert tracked_client.usage_by_model["claude-sonnet-5"]["output_tokens"] == 4000

    estimated_cost = round(estimate_cost(tracked_client.usage_by_model), 4)
    assert (
        estimated_cost
        == 500 / 1000000 * 1.00
        + 1000 / 1000000 * 5.00
        + 2000 / 1000000 * 2.00
        + 4000 / 1000000 * 10.00
    )
