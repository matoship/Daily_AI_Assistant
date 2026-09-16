from types import SimpleNamespace
from daily_assistant import factory as factory_module
from daily_assistant.factory import build_client


def test_build_client_online(monkeypatch):
    captured = {}

    def fake_get_settings():
        return SimpleNamespace(anthropic_api_key="test")

    def fake_anthropic_client(api_key: str):
        captured["api_key"] = api_key
        return fake_get_settings().anthropic_api_key

    monkeypatch.setattr(factory_module, "Anthropic", fake_anthropic_client)
    monkeypatch.setattr(factory_module, "get_settings", fake_get_settings)

    client, models = build_client(False)

    assert models["triage"] == "claude-haiku-4-5-20251001"
    assert captured["api_key"] == "test"
    assert isinstance(client._client, factory_module.AnthropicLLMClient)


def test_build_client_local(monkeypatch):
    captured = {}

    setting = SimpleNamespace(base_url="http://localhost:8000/v1", api_key="dummy")

    def fake_openai_client(
        api_key: str,
        base_url: str,
    ):
        captured["api_key"] = api_key
        return setting

    monkeypatch.setattr(factory_module, "OpenAI", fake_openai_client)

    client, models = build_client(True)

    assert models["triage"] == "<vllm model id>"
    assert captured["api_key"] == "dummy"
    assert isinstance(client._client, factory_module.OpenAICompatibleAdapter)