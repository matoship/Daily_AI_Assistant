from daily_assistant.models import Article, TriageResult
from collections import defaultdict


def select_for_synthesis(
    triaged: list[tuple[Article, TriageResult]], threshold: int, top_n_per_category: int
) -> list[tuple[Article, TriageResult]]:
    """
    Select articles for synthesis based on their triage results.

    Args:
        triaged (list[tuple[Article, TriageResult]]): A list of tuples containing articles and their corresponding triage results.
        threshold (int): The minimum relevance score required for an article to be considered for synthesis.
        top_n_per_category (int): The maximum number of articles to select per category.

    Returns:
        list[tuple[Article, TriageResult]]: A list of selected articles and their corresponding triage results, filtered and ranked based on relevance and category.

    """

    # Filter articles based on the relevance threshold
    filtered = [
        (article, result)
        for article, result in triaged
        if result.relevance >= threshold
    ]

    by_category = defaultdict(list)
    for article, result in filtered:
        by_category[result.category].append((article, result))

    selected = []
    for articles in by_category.values():
        ranked = sorted(articles, key=lambda x: x[1].relevance, reverse=True)
        selected.extend(ranked[:top_n_per_category])

    return selected
