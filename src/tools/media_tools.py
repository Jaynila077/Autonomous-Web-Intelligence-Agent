import os
from typing import List, Dict, Any
from langchain_core.tools import tool
from src.tools.cache_manager import cache_result


def _search_youtube_official(query: str, max_results: int) -> List[Dict[str, Any]]:
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise RuntimeError("YOUTUBE_API_KEY not set")

    from googleapiclient.discovery import build

    youtube = build("youtube", "v3", developerKey=api_key)
    response = (
        youtube.search()
        .list(q=query, part="snippet", type="video", maxResults=max_results, order="relevance")
        .execute()
    )

    results = []
    for item in response.get("items", []):
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]
        results.append({
            "title": snippet.get("title", "Unknown title"),
            "author": snippet.get("channelTitle"),
            "created": snippet.get("publishedAt"),
            "text": snippet.get("description"),
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "source_platform": "YouTube",
        })
    return results


def _search_youtube_no_key(query: str, max_results: int) -> List[Dict[str, Any]]:
    from yt_dlp import YoutubeDL

    search_query = f"ytsearch{max_results}:{query}"
    ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "skip_download": True}

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search_query, download=False)
        entries = info.get("entries", []) if info else []

    results = []
    for entry in entries:
        if not entry:
            continue
        video_id = entry.get("id")
        results.append({
            "title": entry.get("title", "Unknown title"),
            "author": entry.get("channel") or entry.get("uploader"),
            "created": None,
            "text": None,
            "duration": entry.get("duration"),
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "source_platform": "YouTube (Keyless)",
        })
    return results


@cache_result(expire=21600, prefix="youtube")
def _fetch_youtube(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    try:
        return _search_youtube_official(query, max_results)
    except Exception as official_error:
        try:
            return _search_youtube_no_key(query, max_results)
        except Exception as keyless_error:
            return [{
                "error": (
                    f"YouTube search failed via official API ({str(official_error)}) "
                    f"and via keyless fallback ({str(keyless_error)})."
                )
            }]


@tool
def search_youtube(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Searches YouTube for videos matching a query (cached 6h).
    Uses the official Data API v3 when YOUTUBE_API_KEY is set; automatically falls
    back to a keyless yt-dlp-based search if the key is missing, rate-limited, or the
    official call otherwise fails -- so this tool works with or without an API key.
    Use this tool when video content (talks, demos, interviews) is likely to be
    relevant. To read a video's full transcript, pass the returned 'video_id'
    into extract_youtube_transcript.

    Args:
        query: The search topic or keywords.
        max_results: Maximum number of videos to retrieve (default is 10).

    Returns:
        List of dictionaries with video metadata, including 'video_id' for use
        with extract_youtube_transcript. Transcripts are NOT fetched here -- only
        on demand via extract_youtube_transcript, to avoid paying transcript-fetch
        cost for videos the agent doesn't end up using.
    """
    return _fetch_youtube(query=query, max_results=max_results)