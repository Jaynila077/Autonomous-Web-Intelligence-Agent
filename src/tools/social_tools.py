import os
import html
import re
import requests
from langchain_core.tools import tool
from typing import List, Dict, Any

DEFAULT_TIMEOUT = 10

def _strip_html(raw: str) -> str:
    text = re.sub(r"<script.*?</script>", "", raw, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


@tool
def search_reddit(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Searches Reddit public posts for discussion & community opinions."""
    headers = {"User-Agent": "AWIS-OSINT-Agent/2.0"}
    try:
        resp = requests.get(
            "https://www.reddit.com/search.json",
            params={"q": query, "limit": limit, "sort": "relevance"},
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        results = []
        for child in resp.json().get("data", {}).get("children", []):
            d = child.get("data", {})
            results.append({
                "title": d.get("title", ""),
                "url": "https://www.reddit.com" + d.get("permalink", ""),
                "author": d.get("author"),
                "score": d.get("score"),
                "selftext": (d.get("selftext") or "")[:300],
                "subreddit": d.get("subreddit"),
                "source_platform": "Reddit"
            })
        return results
    except Exception as e:
        return [{"error": f"Reddit search error: {str(e)}"}]


@tool
def search_bluesky(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Searches Bluesky (AT Protocol) posts."""
    headers = {"User-Agent": "AWIS-OSINT-Agent/2.0"}
    try:
        resp = requests.get(
            "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts",
            params={"q": query, "limit": limit},
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        results = []
        for post in resp.json().get("posts", []):
            author = post.get("author", {}).get("handle", "")
            text = post.get("record", {}).get("text", "")
            results.append({
                "title": text[:80] if text else "(no text)",
                "text": text,
                "author": author,
                "likes": post.get("likeCount"),
                "source_platform": "Bluesky"
            })
        return results
    except Exception as e:
        return [{"error": f"Bluesky search error: {str(e)}"}]


@tool
def search_mastodon(query: str, instance: str = "mastodon.social", limit: int = 5) -> List[Dict[str, Any]]:
    """Searches Mastodon public posts on a specified instance."""
    try:
        resp = requests.get(
            f"https://{instance}/api/v2/search",
            params={"q": query, "type": "statuses", "limit": limit},
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        results = []
        for status in resp.json().get("statuses", []):
            content = _strip_html(status.get("content", ""))
            results.append({
                "preview": content[:100],
                "url": status.get("url", ""),
                "author": status.get("account", {}).get("acct"),
                "content": content,
                "source_platform": f"Mastodon ({instance})"
            })
        return results
    except Exception as e:
        return [{"error": f"Mastodon search error: {str(e)}"}]


@tool
def search_lemmy(query: str, instance: str = "lemmy.world", limit: int = 5) -> List[Dict[str, Any]]:
    """Searches Lemmy fediverse community posts."""
    headers = {"User-Agent": "AWIS-OSINT-Agent/2.0"}
    try:
        resp = requests.get(
            f"https://{instance}/api/v3/search",
            params={"q": query, "type_": "Posts", "sort": "TopAll", "limit": limit},
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        results = []
        for item in resp.json().get("posts", []):
            post = item.get("post", {})
            results.append({
                "title": post.get("name", ""),
                "url": post.get("ap_id", ""),
                "author": item.get("creator", {}).get("name"),
                "body": (post.get("body") or "")[:300],
                "source_platform": f"Lemmy ({instance})"
            })
        return results
    except Exception as e:
        return [{"error": f"Lemmy search error: {str(e)}"}]


@tool
def search_tumblr(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Searches Tumblr posts by tag. Requires TUMBLR_API_KEY."""
    api_key = os.environ.get("TUMBLR_API_KEY")
    if not api_key:
        return [{"error": "TUMBLR_API_KEY environment variable is not set."}]

    tag = query.strip().replace(" ", "")
    try:
        resp = requests.get(
            "https://api.tumblr.com/v2/tagged",
            params={"tag": tag, "api_key": api_key, "limit": limit},
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        results = []
        for post in resp.json().get("response", []):
            body = _strip_html(post.get("summary") or post.get("caption") or "")
            results.append({
                "title": body[:80] or "(untitled post)",
                "url": post.get("post_url", ""),
                "author": post.get("blog_name"),
                "source_platform": "Tumblr"
            })
        return results
    except Exception as e:
        return [{"error": f"Tumblr API error: {str(e)}"}]


@tool
def search_vk(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Searches VKontakte (VK) newsfeed posts. Requires VK_ACCESS_TOKEN."""
    token = os.environ.get("VK_ACCESS_TOKEN")
    if not token:
        return [{"error": "VK_ACCESS_TOKEN environment variable is not set."}]

    params = {"q": query, "count": limit, "access_token": token, "v": "5.199"}
    try:
        resp = requests.get("https://api.vk.com/method/newsfeed.search", params=params, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            return [{"error": f"VK error: {data['error'].get('error_msg')}"}]

        results = []
        for item in data.get("response", {}).get("items", []):
            text = item.get("text", "")
            results.append({
                "title": text[:80] if text else "(no text)",
                "url": f"https://vk.com/wall{item.get('owner_id')}_{item.get('id')}",
                "text": text[:300],
                "source_platform": "VKontakte"
            })
        return results
    except Exception as e:
        return [{"error": f"VK API error: {str(e)}"}]
