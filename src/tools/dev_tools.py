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

    Returns:
        List of dictionaries with repo metadata, including 'full_name' (owner/repo)
        for use with extract_github_readme.
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
def search_stackexchange(query: str, max_results: int = 10, site: str = "stackoverflow") -> List[Dict[str, Any]]:
    """
    Searches Stack Exchange (Stack Overflow by default) for questions and answers (cached 6h).
    Use this tool when researching a technical/programming problem, error message,
    or "how do I..." style question where practitioner Q&A is likely to have the answer.
    The 'text' field is a preview capped at ~300 characters (SO answers routinely
    contain long code blocks) -- follow the returned 'url' if you need the full body.
    No API key is required for normal usage.

    Args:
        query: The search topic or technical keywords.
        max_results: Maximum number of questions to retrieve (default is 10).
        site: The Stack Exchange site to search (default is 'stackoverflow').

    Returns:
        List of dictionaries with question metadata, including a capped preview of
        the question body text.
    """
    params = {
        "q": query,
        "site": site,
        "pagesize": max_results,
        "order": "desc",
        "sort": "relevance",
        "filter": "withbody",
    }
    api_key = os.environ.get("STACKEXCHANGE_API_KEY")
    if api_key:
        params["key"] = api_key

    try:
        resp = requests.get(
            "https://api.stackexchange.com/2.3/search/advanced",
            params=params, timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("items", []):
            body = _strip_html_tags(item.get("body", ""))
            preview = body[:300] + "..." if len(body) > 300 else body
            results.append({
                "title": _strip_html_tags(item.get("title", "")),
                "author": item.get("owner", {}).get("display_name"),
                "created": str(item.get("creation_date")),
                "score": item.get("score"),
                "text": preview,
                "url": item.get("link", ""),
                "answer_count": item.get("answer_count"),
                "is_answered": item.get("is_answered"),
                "tags": item.get("tags"),
                "source_platform": f"StackExchange ({site})",
            })
        return results
    except Exception as e:
        return [{"error": f"StackExchange API error: {str(e)}"}]