import os
import html
import re
import requests
from langchain_core.tools import tool
from typing import List, Dict, Any

DEFAULT_TIMEOUT = 10

def _strip_html_tags(raw: str) -> str:
    text = re.sub(r"<script.*?</script>", "", raw, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


@tool
def search_github_repos(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Searches GitHub repositories matching a query, sorted by star count.
    Use this tool FIRST when a request needs open-source projects, tools,
    or code examples related to a topic.

    Args:
        query: The search query (e.g. 'agentic ai framework').
        limit: Maximum number of repositories to retrieve (default is 5).
    """
    params = {"q": query, "per_page": limit, "sort": "stars", "order": "desc"}
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.get("https://api.github.com/search/repositories", params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        
        return [
            {
                "full_name": item.get("full_name", ""),
                "url": item.get("html_url", ""),
                "owner": item.get("owner", {}).get("login"),
                "stars": item.get("stargazers_count"),
                "description": item.get("description"),
                "language": item.get("language"),
                "source_platform": "GitHub"
            }
            for item in data.get("items", [])
        ]
    except Exception as e:
        return [{"error": f"GitHub API error: {str(e)}"}]


@tool
def search_stackexchange(query: str, site: str = "stackoverflow", limit: int = 5) -> List[Dict[str, Any]]:
    """
    Searches Stack Exchange sites (e.g. Stack Overflow) for technical/programming Q&A.
    """
    params = {
        "q": query,
        "site": site,
        "pagesize": limit,
        "order": "desc",
        "sort": "relevance",
        "filter": "withbody",
    }
    api_key = os.environ.get("STACKEXCHANGE_API_KEY")
    if api_key:
        params["key"] = api_key

    try:
        resp = requests.get("https://api.stackexchange.com/2.3/search/advanced", params=params, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        
        return [
            {
                "title": _strip_html_tags(item.get("title", "")),
                "url": item.get("link", ""),
                "score": item.get("score"),
                "body": _strip_html_tags(item.get("body", ""))[:300] + "...",
                "is_answered": item.get("is_answered"),
                "tags": item.get("tags"),
                "source_platform": f"StackExchange ({site})"
            }
            for item in data.get("items", [])
        ]
    except Exception as e:
        return [{"error": f"StackExchange API error: {str(e)}"}]
