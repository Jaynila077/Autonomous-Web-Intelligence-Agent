import os
from langchain_core.tools import tool
from typing import List, Dict, Any, Optional

@tool
def search_youtube_transcripts(
    query: str, max_results: int = 3, languages: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Searches YouTube via official Data API v3 and fetches each result's transcript.
    Requires YOUTUBE_API_KEY environment variable.
    """
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        return search_youtube_transcripts_no_key.invoke({"query": query, "max_results": max_results})

    if languages is None:
        languages = ["en"]

    try:
        from googleapiclient.discovery import build
        from youtube_transcript_api import YouTubeTranscriptApi
        
        youtube = build("youtube", "v3", developerKey=api_key)
        response = (
            youtube.search()
            .list(q=query, part="snippet", type="video", maxResults=max_results, order="relevance")
            .execute()
        )
        ytt_api = YouTubeTranscriptApi()
        results = []

        for item in response.get("items", []):
            video_id = item["id"]["videoId"]
            snippet = item["snippet"]
            video_data = {
                "title": snippet.get("title", "Unknown title"),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "channel": snippet.get("channelTitle"),
                "published_at": snippet.get("publishedAt"),
                "transcript": None,
                "source_platform": "YouTube"
            }
            try:
                fetched_transcript = ytt_api.fetch(video_id, languages=languages)
                video_data["transcript"] = " ".join(s.text for s in fetched_transcript)[:2000]
            except Exception as e:
                video_data["transcript_error"] = str(e)

            results.append(video_data)
        return results
    except Exception as e:
        return search_youtube_transcripts_no_key.invoke({"query": query, "max_results": max_results})


@tool
def search_youtube_transcripts_no_key(
    query: str, max_results: int = 3, languages: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Searches YouTube via yt-dlp (no API key required) and fetches video transcripts.
    """
    if languages is None:
        languages = ["en"]

    try:
        from yt_dlp import YoutubeDL
        from youtube_transcript_api import YouTubeTranscriptApi

        search_query = f"ytsearch{max_results}:{query}"
        ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "skip_download": True}
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            entries = info.get("entries", []) if info else []

        ytt_api = YouTubeTranscriptApi()
        results = []

        for entry in entries:
            if not entry:
                continue
            video_id = entry.get("id")
            video_data = {
                "title": entry.get("title", "Unknown title"),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "channel": entry.get("channel") or entry.get("uploader"),
                "duration": entry.get("duration"),
                "transcript": None,
                "source_platform": "YouTube (Keyless)"
            }
            try:
                fetched_transcript = ytt_api.fetch(video_id, languages=languages)
                video_data["transcript"] = " ".join(s.text for s in fetched_transcript)[:2000]
            except Exception as e:
                video_data["transcript_error"] = str(e)

            results.append(video_data)
        return results
    except Exception as e:
        return [{"error": f"yt-dlp YouTube search failed: {str(e)}"}]
