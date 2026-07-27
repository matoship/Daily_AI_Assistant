
from daily_assistant.models import Article, TriageResult


def select_for_synthesis(triaged: list[tuple[Article,TriageResult]],threshold:int,top_n:int) -> list[tuple[Article,TriageResult]]:
    """
    Select articles for synthesis based on triage results.
    
    Args:
        triaged (list[tuple[Article, TriageResult]]): A list of tuples containing articles and their corresponding triage results.
        threshhold (int): The minimum relevance score required for an article to be considered.
        top_n (int): The maximum number of articles to select.
    
    Returns:
        list[tuple[Article, TriageResult]]: A list of selected articles and their triage results.
    """
    # Filter articles based on the relevance threshold
    filtered = [(article, result) for article, result in triaged if result.relevance >= threshold]
    
    # Sort the filtered articles by relevance in descending order
    sorted_articles = sorted(filtered, key=lambda x: x[1].relevance, reverse=True)
    
    # Return the top N articles
    return sorted_articles[:top_n]