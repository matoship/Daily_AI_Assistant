from daily_assistant.config import Settings


def test_settings_loads_from_env(monkeypatch):
    # Set the environment variable for testing
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_api_key")

    settings = Settings()

    assert settings.anthropic_api_key == "test_api_key"


def test_settings_missing_env_var(monkeypatch):
    # Ensure the environment variable is not set
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    settings = Settings(_env_file=None)

    assert settings.anthropic_api_key is None
