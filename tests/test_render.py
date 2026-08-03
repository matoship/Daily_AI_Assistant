from daily_assistant.render import render_digest_page, render_index

def test_render_digest_page():
    digest = [
        {
            "headline": "Test Headline 1",
            "summary": "This is a summary of the first test article.",
            "why_it_matters": "This article is important because it provides insights into testing.",
            "category": "Testing",
            "article_urls": ["http://example.com/article1", "http://example.com/article2"]
        },
        {
            "headline": "Test Headline 2",
            "summary": "This is a summary of the second test article.",
            "why_it_matters": "This article is important because it discusses best practices.",
            "category": "Best Practices",
            "article_urls": ["http://example.com/article3"]
        }
    ]
    date = "2024-06-01"
    html_output = render_digest_page(digest, date)
    
    assert "<h1>Daily Digest for 2024-06-01</h1>" in html_output
    assert "<h2>Test Headline 1</h2>" in html_output
    assert "<p>This is a summary of the first test article.</p>" in html_output
    assert "<strong>Why it matters:</strong> This article is important because it provides insights into testing." in html_output
    assert "<strong>Category:</strong> Testing" in html_output
    assert "<strong>Articles:</strong> http://example.com/article1; http://example.com/article2" in html_output

def test_render_index():
    archive_dates = ["2024-06-01", "2024-06-02", "2024-06-03"]
    html_output = render_index(archive_dates)

    assert "<h1>Daily Digest Archive</h1>" in html_output
    assert "<li><a href='digest_2024-06-01.html'>2024-06-01</a></li>" in html_output
    assert "<li><a href='digest_2024-06-02.html'>2024-06-02</a></li>" in html_output
    assert "<li><a href='digest_2024-06-03.html'>2024-06-03</a></li>" in html_output