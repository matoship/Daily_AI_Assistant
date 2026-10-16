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

    def fake_get_settings():
        return SimpleNamespace(
            local_model="test-local-model",
            vllm_base_url="http://localhost:8000/v1",
            local_api_key="dummy",
        )

    monkeypatch.setattr(factory_module, "get_settings", fake_get_settings)

    client, models = build_client(True)

    assert client._client._client.base_url == "http://localhost:8000/v1/"
    assert client._client._client.api_key == "dummy"
    assert models["triage"] == "test-local-model"
    assert models["synthesis"] == "test-local-model"
    assert isinstance(client._client, factory_module.OpenAICompatibleAdapter)


def test_build_client_missing_Anthropic_key(monkeypatch):
    def fake_get_settings():
        return SimpleNamespace(anthropic_api_key=None)

    monkeypatch.setattr(factory_module, "get_settings", fake_get_settings)

    try:
        build_client(False)
    except ValueError as e:
        assert str(e) == "Anthropic API key must be configured"
