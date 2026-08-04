import os
import random
import requests
from langchain_core.tools import tool
from typing import List, Dict, Any, Optional
from src.tools.cache_manager import cache_result, truncate_tool_output

DEFAULT_TIMEOUT = 10

@cache_result(expire=86400, prefix="wiki")
def _fetch_wiki_data(query: str, lang: str = "en") -> Dict[str, Any]:
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "titles": query,
        "prop": "extracts|extlinks|links",
        "explaintext": True,
        "exsectionformat": "plain",
        "pllimit": "max"
    }
    headers = {"User-Agent": "AWIS_Intelligence_System/2.0"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        pages = response.json().get("query", {}).get("pages", {})

        for page_id, page_info in pages.items():
            if page_id == "-1":
                return {"error": f"No Wikipedia page found for '{query}'"}

            return {
                "title": page_info.get("title"),
                "content": page_info.get("extract", "No content available."),
                "internal_links_count": len(page_info.get("links", [])),
                "source_url": f"https://{lang}.wikipedia.org/wiki/{query.replace(' ', '_')}",
                "source_platform": "Wikipedia"
            }

        return {"error": f"No Wikipedia page found for '{query}'"}

    except Exception as e:
        return {"error": f"Wikipedia API Request failed: {str(e)}"}


@tool
def fetch_wiki_data(query: str, lang: str = "en") -> str:
    """
    Fetches a structured summary of a Wikipedia article via MediaWiki API (Cached 24h).
    """
    res = _fetch_wiki_data(query=query, lang=lang)
    return truncate_tool_output(res, max_chars=1200)


@cache_result(expire=86400, prefix="tavily")
def _fetch_tavily(query: str, max_results: int = 3) -> Dict[str, Any]:
    try:
        from tavily import TavilyClient
    except ImportError:
        return {"warning": "[Tool Unavailable] 'tavily-python' library is not installed. Run `pip install tavily-python`."}

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return {"warning": "[Tool Unavailable] TAVILY_API_KEY environment variable is not set."}

    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
            topic="general",
            include_answer=False,
        )
        return {
            "answer": response.get("answer"),
            "results": [
                {
                    "title": r.get("title"),
                    "url": r.get("url"),
                    "score": r.get("score"),
                    "content": r.get("content"),
                    "source_platform": "Tavily Web"
                }
                for r in response.get("results", [])
            ],
        }
    except Exception as e:
        return {"error": f"Tavily search failed: {str(e)}"}


@tool
def search_tavily(
    query: str,
    max_results: int = 3,
    search_depth: str = "basic",
    topic: str = "general",
    include_answer: bool = False
) -> str:
    """
    Runs a structured web search via Tavily API with relevance scoring (Cached 24h).
    """
    res = _fetch_tavily(query=query, max_results=max_results)
    return truncate_tool_output(res, max_chars=1200)


@tool
def search_web_news(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Searches the general web and live headlines via DuckDuckGo.
    """
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return [{"warning": "[Tool Unavailable] 'duckduckgo-search' library is not installed. Run `pip install duckduckgo-search`."}]

    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
        if not raw_results:
            return [{"error": f"No news results found for '{query}'"}]

        return [
            {
                "title": article.get("title", "No Title"),
                "link": article.get("href", "No Link"),
                "snippet": article.get("body", "No Snippet"),
                "source_platform": "DuckDuckGo News"
            }
            for article in raw_results
        ]
    except Exception as e:
        return [{"error": f"DuckDuckGo search error: {str(e)}"}]


@tool
def search_exa_semantic(semantic_query: str, max_links: int = 2) -> List[Dict[str, Any]]:
    """
    Runs a neural/semantic web search via Exa API and returns extracted highlights.
    """
    try:
        from exa_py import Exa
    except ImportError:
        return [{"warning": "[Tool Unavailable] 'exa-py' library is not installed. Run `pip install exa-py`."}]

    api_key = os.environ.get("EXA_API_KEY")
    if not api_key:
        return [{"warning": "[Tool Unavailable] EXA_API_KEY environment variable is not set."}]

    try:
        from exa_py import Exa
        exa = Exa(api_key=api_key)

        response = exa.search(
            semantic_query,
            type="auto",
            num_results=max_links,
            contents={"highlights": True},
        )
        results = response.results
        if not results:
            return [{"error": "No semantic matches found."}]

        return [
            {
                "title": article.title,
                "url": article.url,
                "highlights": [h.replace("\n", " ").strip() for h in article.highlights] if article.highlights else [],
                "source_platform": "Exa Semantic"
            }
            for article in results
        ]
    except Exception as e:
        return [{"error": f"Exa API call failed: {str(e)}"}]


@tool
def find_working_searxng(min_uptime_pct: float = 90.0, max_instances: int = 5) -> List[Dict[str, Any]]:
    """
    Discovers currently reachable, publicly-hosted SearXNG instances.
    """
    directory_url = "https://searx.space/data/instances.json"
    try:
        directory_response = requests.get(directory_url, timeout=DEFAULT_TIMEOUT)
        instances = directory_response.json().get("instances", {})
    except Exception as e:
        return [{"error": f"Failed to fetch SearXNG directory: {str(e)}"}]

    candidates = [
        url.rstrip("/")
        for url, info in instances.items()
        if url.startswith("https://")
        and info.get("uptime", {}).get("uptimeDay", 0) > min_uptime_pct
    ]
    random.shuffle(candidates)

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    working_instances = []

    for base_url in candidates:
        if len(working_instances) >= max_instances:
            break
        try:
            json_response = requests.get(
                f"{base_url}/search",
                params={"q": "Technology", "format": "json"},
                headers=headers,
                timeout=5,
            )
            if json_response.status_code == 200 and json_response.json().get("results"):
                working_instances.append({"url": base_url, "response_type": "json", "source_platform": "SearXNG"})
        except Exception:
            continue

    return working_instances if working_instances else [{"error": "No working SearXNG instances found."}]


@tool
def search_site_content(domain: str, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Searches for content within a specific domain via a 'site:' dork query.
    """
    dork_query = f"site:{domain} {query}"
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(dork_query, max_results=max_results))
        if not raw_results:
            return [{"error": f"No results found on '{domain}' for '{query}'"}]

        return [
            {
                "title": result.get("title", "No Title"),
                "link": result.get("href", "No Link"),
                "snippet": result.get("body", "No Snippet"),
                "source_platform": f"Site Search ({domain})"
            }
            for result in raw_results
        ]
    except Exception as e:
        return [{"error": f"Site dork search failed: {str(e)}"}]


@tool
def find_site_feeds(domain: str) -> List[Dict[str, Any]]:
    """
    Discovers a website's RSS/Atom/JSON syndication feeds.
    """
    try:
        from feedsearch_crawler import search as search_feeds
        feeds = search_feeds(domain)
        if not feeds:
            return [{"error": f"No syndication feeds found for '{domain}'."}]

        return [
            {
                "url": str(feed.url),
                "title": feed.title if feed.title else "Untitled Feed",
                "content_type": feed.content_type if feed.content_type else "Unknown Format",
                "source_platform": "RSS/Atom Feed"
            }
            for feed in feeds
        ]
    except Exception as e:
        return [{"error": f"Feed discovery failed: {str(e)}"}]
