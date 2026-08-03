from typing import Any

from daily_assistant.models import DigestItem

import html

def _coerce_digest_item(item: DigestItem | dict[str, Any]) -> DigestItem:
    if isinstance(item, DigestItem):
        return item
    if isinstance(item, dict):
        return DigestItem(**item)
    raise TypeError(f"Expected DigestItem or dict, got {type(item).__name__}")


def render_digest_page(digest: list[DigestItem | dict[str, Any]], date: str) -> str:
    """
    Render the digest page as an HTML string.

    Args:
        digest (list[DigestItem | dict[str, Any]]): A list of digest items to be displayed on the page.
        date (str): The date for which the digest is generated.

    Returns:
        str: An HTML string representing the digest page.
    """
    html_content = f"<html><head><title>Daily Digest - {html.escape(date)}</title></head><body>"
    html_content += f"<h1>Daily Digest for {html.escape(date)}</h1>"

    for item in digest:
        normalized_item = _coerce_digest_item(item)
        html_content += f"<div class='digest-item'>"
        html_content += f"<h2>{html.escape(normalized_item.headline)}</h2>"
        html_content += f"<p>{html.escape(normalized_item.summary)}</p>"
        html_content += f"<p><strong>Why it matters:</strong> {html.escape(normalized_item.why_it_matters)}</p>"
        html_content += f"<p><strong>Category:</strong> {html.escape(normalized_item.category)}</p>"
        html_content += f"<p><strong>Articles:</strong> {'; '.join(html.escape(url) for url in normalized_item.article_urls)}</p>"
        html_content += "</div><hr>"

    html_content += "</body></html>"
    return html_content

def render_index(archive_dates: list[str]) -> str:
    """
    Render the index page as an HTML string.

    Args:
        archive_dates (list[str]): A list of dates for which digests are available.

    Returns:
        str: An HTML string representing the index page.
    """
    html_content = "<html><head><title>Daily Digest Archive</title></head><body>"
    html_content += "<h1>Daily Digest Archive</h1>"
    html_content += "<ul>"
    for date in archive_dates:
        html_content += f"<li><a href='digest_{html.escape(date)}.html'>{html.escape(date)}</a></li>"
    html_content += "</ul>"
    html_content += "</body></html>"
    return html_content