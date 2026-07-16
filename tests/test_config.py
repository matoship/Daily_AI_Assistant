from daily_assistant.config import Settings

def test_settings_loads_from_env(monkeypatch):
    # Set the environment variable for testing
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_api_key")
    
    settings = Settings()
    
    assert settings.anthropic_api_key == "test_api_key"

