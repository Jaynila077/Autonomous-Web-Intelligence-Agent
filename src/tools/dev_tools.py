import os
import re
import html
import requests
from typing import List, Dict, Any
from langchain_core.tools import tool
from src.tools.cache_manager import cache_result

DEFAULT_TIMEOUT = 10


def _strip_html_tags(raw: str) -> str:
    text = re.sub(r"<script.*?</script>", "", raw or "", flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


@cache_result(expire=86400, prefix="github")
def _fetch_github_repos(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    params = {"q": query, "per_page": max_results, "sort": "stars", "order": "desc"}
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.get(
            "https://api.github.com/search/repositories",
            params=params, headers=headers, timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        return [
            {
                "full_name": item.get("full_name", ""),
                "author": item.get("owner", {}).get("login"),
                "created": item.get("created_at"),
                "stars": item.get("stargazers_count"),
                "forks": item.get("forks_count"),
                "language": item.get("language"),
                "text": item.get("description"),
                "url": item.get("html_url", ""),
                "source_platform": "GitHub",
            }
            for item in data.get("items", [])
        ]
    except Exception as e:
        return [{"error": f"GitHub API error: {str(e)}"}]


@tool
def search_github_repos(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Searches GitHub for public repositories matching a query, sorted by stars (cached 24h).
    Use this tool when researching what tools/libraries/projects exist for a topic,
    or when you need a repo's full_name (owner/repo) to pass into extract_github_readme
    for the project's full README content.
    No API key required; set GITHUB_TOKEN in the environment to raise the rate limit.

    Args:
        query: The search topic or technical keywords.
        max_results: Maximum number of repositories to retrieve (default is 10).

    Returns:
        List of dictionaries with repo metadata, including 'full_name' (owner/repo)
        for use with extract_github_readme.
    """
    return _fetch_github_repos(query=query, max_results=max_results)


@cache_result(expire=21600, prefix="stackexchange")
def _fetch_stackexchange(query: str, max_results: int = 10, site: str = "stackoverflow") -> List[Dict[str, Any]]:
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
    return _fetch_stackexchange(query=query, max_results=max_results, site=site)