from daily_assistant.profile import load_profile, load_sources, category_options

def test_load_profile():
    profile = load_profile()
    assert isinstance(profile, dict)
    assert "identity" in profile
    assert "topics" in profile
    
def test_load_sources():
    sources = load_sources()
    assert isinstance(sources, list)
    for source in sources:
        assert "url" in source
        assert "name" in source
        assert "justification" in source

def test_category_options():
    profile = load_profile()
    categories = category_options(profile)
    assert isinstance(categories, list)
    for category in categories:
        assert isinstance(category, str)