from types import SimpleNamespace

from daily_assistant.telemetry import TrackedClient, estimate_cost

def test_tracked_client():
    # Create a mock Anthropic client
    class MockAnthropicClient:
        def __init__(self):
            self.messages = self.MockMessages()

        class MockMessages:
            def create(self, model, max_tokens, tools, tool_choice, messages):
                # Return a mock response with usage information
                return SimpleNamespace(
                    model=model,
                    usage=SimpleNamespace(input_tokens=1000, output_tokens=2000)
                )

    mock_client = MockAnthropicClient()
    tracked_client = TrackedClient(mock_client)

    # Simulate a message creation
    tracked_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        tools=[],
        tool_choice=None,
        messages=[]
    )

    # Check if the usage was recorded correctly
    assert tracked_client.usage_by_model["claude-haiku-4-5-20251001"]["input_tokens"] == 1000
    assert tracked_client.usage_by_model["claude-haiku-4-5-20251001"]["output_tokens"] == 2000

    # Estimate cost based on the recorded usage
    estimated_cost = estimate_cost(tracked_client.usage_by_model)
    expected_cost = 0.001 + 0.01  # Based on PRICING
    assert estimated_cost == expected_cost

def test_token_counting_with_different_models():
    # Create a mock Anthropic client
    class MockAnthropicClient:
        def __init__(self):
            self.messages = self.MockMessages()

        class MockMessages:
            def create(self, model, max_tokens, tools, tool_choice, messages):
                # Return a mock response with usage information
                if model == "claude-haiku-4-5-20251001":
                    return SimpleNamespace(
                        model=model,
                        usage=SimpleNamespace(input_tokens=500, output_tokens=1000)
                    )
                elif model == "claude-sonnet-5":
                    return SimpleNamespace(
                        model=model,
                        usage=SimpleNamespace(input_tokens=2000, output_tokens=4000)
                    )
                else:
                    return SimpleNamespace(
                        model=model,
                        usage=SimpleNamespace(input_tokens=0, output_tokens=0)
                    )

    mock_client = MockAnthropicClient()
    tracked_client = TrackedClient(mock_client)

    # Simulate message creation for different models
    tracked_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        tools=[],
        tool_choice=None,
        messages=[]
    )
    tracked_client.messages.create(
        model="claude-sonnet-5",
        max_tokens=200,
        tools=[],
        tool_choice=None,
        messages=[]
    )

    # Check if the usage was recorded correctly for both models
    assert tracked_client.usage_by_model["claude-haiku-4-5-20251001"]["input_tokens"] == 500
    assert tracked_client.usage_by_model["claude-haiku-4-5-20251001"]["output_tokens"] == 1000
    assert tracked_client.usage_by_model["claude-sonnet-5"]["input_tokens"] == 2000
    assert tracked_client.usage_by_model["claude-sonnet-5"]["output_tokens"] == 4000

    # Estimate cost based on the recorded usage
    estimated_cost = round( estimate_cost(tracked_client.usage_by_model),4)
    assert estimated_cost == 500/1000000 * 1.00 + 1000/1000000 * 5.00 + 2000/1000000 * 2.00 + 4000/1000000 * 10.00