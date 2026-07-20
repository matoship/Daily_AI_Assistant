from daily_assistant.profile import load_profile

def test_load_profile():
    profile = load_profile()
    assert isinstance(profile, dict)
    assert "identity" in profile
    assert "immigration" in profile