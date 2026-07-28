from langchain_core.tools import tool
from typing import List, Dict, Any

#example
@tool
def search_news_and_web(query: str) -> List[Dict[str, str]]:
    """
    Searches the live internet for recent news, PR releases, and web articles.
    Use this tool FIRST to discover target URLs and metadata related to a topic.
    Returns a list of dicts with 'url', 'title', and 'snippet'.
    """
    # Placeholder: Connect your Tavily / DDGS / web-scope-extract logic here
    return [
        {"url": "https://example.com/news1", "title": "Sample News Title", "snippet": "Sample snippet..."}
    ]

@tool
def search_academic_arxiv(query: str) -> List[Dict[str, str]]:
    """
    Searches arXiv for scientific research papers and pre-prints.
    Returns abstracts, authors, and direct PDF download links.
    """
    return [
        {"url": "https://arxiv.org/pdf/sample.pdf", "title": "Sample Paper", "snippet": "Abstract content..."}
    ]
