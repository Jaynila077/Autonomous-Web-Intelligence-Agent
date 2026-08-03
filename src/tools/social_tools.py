import os
import html
import re
import requests
from typing import List, Dict, Any
from src.tools.cache_manager import cache_result

DEFAULT_TIMEOUT = 10

def _strip_html(raw: str) -> str:
    text = re.sub(r"<script.*?</script>", "", raw, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()

@cache_result(expire=3600, prefix="mastodon")
def _fetch_mastodon(query: str, max_results: int = 10, instance: str = "mastodon.social") -> List[Dict[str, Any]]:
    try:
        resp = requests.get(
            f"https://{instance}/api/v2/search",
            params={"q": query, "type": "statuses", "limit": max_results},
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        results = []
        for status in resp.json().get("statuses", []):
            content = _strip_html(status.get("content", ""))
            account = status.get("account", {})
            results.append({
                "title": content[:80],
                "author": account.get("acct"),
                "created": status.get("created_at"),
                "favourites": status.get("favourites_count"),
                "reblogs": status.get("reblogs_count"),
                "text": content,
                "url": status.get("url", ""),
                "source_platform": f"Mastodon ({instance})",
            })
        return results
    except Exception as e:
        return [{"error": f"Mastodon search error: {str(e)}"}]

def search_mastodon(query: str, max_results: int = 10, instance: str = "mastodon.social") -> List[Dict[str, Any]]:
    """
    Searches public statuses on a single Mastodon instance (cached 1h).
    """
    return _fetch_mastodon(query=query, max_results=max_results, instance=instance)

@cache_result(expire=3600, prefix="lemmy")
def _fetch_lemmy(query: str, max_results: int = 10, instance: str = "lemmy.world") -> List[Dict[str, Any]]:
    headers = {"User-Agent": "AWIS-OSINT-Agent/2.0"}
    try:
        resp = requests.get(
            f"https://{instance}/api/v3/search",
            params={"q": query, "type_": "Posts", "sort": "TopAll", "limit": max_results},
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        results = []
        for item in resp.json().get("posts", []):
            post = item.get("post", {})
            counts = item.get("counts", {})
            creator = item.get("creator", {})
            community = item.get("community", {})
            body = post.get("body") or ""
            preview = body[:300] + "..." if len(body) > 300 else body
            results.append({
                "title": post.get("name", ""),
                "author": creator.get("name"),
                "created": post.get("published"),
                "score": counts.get("score"),
                "community": community.get("name"),
                "num_comments": counts.get("comments"),
                "text": preview,
                "post_id": post.get("id"),
                "url": post.get("ap_id", ""),
                "source_platform": f"Lemmy ({instance})",
            })
        return results
    except Exception as e:
        return [{"error": f"Lemmy search error: {str(e)}"}]

def search_lemmy(query: str, max_results: int = 10, instance: str = "lemmy.world") -> List[Dict[str, Any]]:
    """
    Searches posts on a single Lemmy instance (cached 1h).
    """
    return _fetch_lemmy(query=query, max_results=max_results, instance=instance)