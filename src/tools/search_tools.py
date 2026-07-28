import io
import os
import random
import requests
import xml.etree.ElementTree as ET
from langchain_core.tools import tool
from typing import List, Dict, Any, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)
from yt_dlp import YoutubeDL
from ddgs import DDGS
from feedsearch_crawler import search as search_feeds

#example
@tool
def search_arxiv(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Searches arXiv for scientific research, pre-prints, and academic papers.
    Use this tool FIRST when researching deep technical, AI/ML, or scientific topics
    to find paper titles, abstracts, authors, and direct PDF URLs.
    
    Args:
        query: The search topic or technical keywords (e.g. 'large language model hallucinations').
        max_results: Maximum number of papers to retrieve (default is 3).
        
    Returns:
        List of dictionaries containing paper metadata and direct 'pdf_link' URLs.
    """
    url = "http://export.arxiv.org/api/query"
    
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return [{"error": f"Failed to fetch arXiv data: HTTP {response.status_code}"}]

        root = ET.fromstring(response.content)
        namespace = {'atom': 'http://www.w3.org/2005/Atom'}
        extracted_papers = []

        for entry in root.findall('atom:entry', namespace):
            title = entry.find('atom:title', namespace).text.replace('\n', ' ').strip()
            summary = entry.find('atom:summary', namespace).text.replace('\n', ' ').strip()
            published_date = entry.find('atom:published', namespace).text
            paper_url = entry.find('atom:id', namespace).text
            
            authors = [
                author.find('atom:name', namespace).text 
                for author in entry.findall('atom:author', namespace)
            ]
            
            pdf_link = next(
                (link.attrib['href'] for link in entry.findall('atom:link', namespace) if link.attrib.get('title') == 'pdf'),
                None
            )

            # Ensure PDF link uses https and ends properly
            if pdf_link and not pdf_link.endswith('.pdf'):
                pdf_link = pdf_link + '.pdf'

            extracted_papers.append({
                "title": title,
                "authors": ", ".join(authors),
                "published": published_date[:10],
                "summary": summary,
                "url": paper_url,
                "pdf_link": pdf_link
            })
            
        return extracted_papers

    except Exception as e:
        return [{"error": f"Error querying arXiv API: {str(e)}"}]


#example
@tool
def find_working_searxng(min_uptime_pct: float = 90.0, max_instances: int = 5) -> List[Dict[str, Any]]:
    """
    Discovers currently reachable, publicly-hosted SearXNG instances.
    Use this tool FIRST whenever a general web search tool is needed but no fixed
    SearXNG endpoint is configured or the configured one is unavailable/rate-limited.
    It pulls the live instance directory, filters for reliable HTTPS hosts, and
    probes each candidate with a test query until enough working instances are found.

    Args:
        min_uptime_pct: Minimum reported 24h uptime percentage required for an
            instance to be considered a candidate (default is 90.0).
        max_instances: Maximum number of confirmed working instances to return
            before stopping the probe loop (default is 5).

    Returns:
        List of dictionaries, each containing a working instance's base 'url'
        and the search 'response_type' it supports ('json' or 'html'), ordered
        by discovery order. Returns a list with a single 'error' dictionary if
        the instance directory itself could not be fetched.
    """
    directory_url = "https://searx.space/data/instances.json"

    try:
        directory_response = requests.get(directory_url, timeout=10)
        instances = directory_response.json().get("instances", {})
    except Exception as e:
        return [{"error": f"Failed to fetch SearXNG instance directory: {str(e)}"}]

    candidates = [
        url.rstrip("/")
        for url, info in instances.items()
        if url.startswith("https://")
        and info.get("uptime", {}).get("uptimeDay", 0) > min_uptime_pct
    ]
    random.shuffle(candidates)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    working_instances = []

    for base_url in candidates:
        if len(working_instances) >= max_instances:
            break
        try:
            json_response = requests.get(
                f"{base_url}/search",
                params={"q": "Apple Inc", "format": "json"},
                headers=headers,
                timeout=5,
            )
            if json_response.status_code == 200 and json_response.json().get("results"):
                working_instances.append({"url": base_url, "response_type": "json"})
                continue

            html_response = requests.get(
                f"{base_url}/search",
                params={"q": "Apple Inc"},
                headers=headers,
                timeout=5,
            )
            if (
                html_response.status_code == 200
                and "not a bot" not in html_response.text.lower()
                and "cloudflare" not in html_response.text.lower()
                and "result" in html_response.text.lower()
            ):
                working_instances.append({"url": base_url, "response_type": "html"})
        except Exception:
            continue

    if not working_instances:
        return [{"error": "No working SearXNG instances found matching the criteria."}]

    return working_instances


#example
@tool
def fetch_wiki_data(query: str, lang: str = "en") -> Dict[str, Any]:
    """
    Fetches a structured summary of a Wikipedia article via the MediaWiki API.
    Use this tool FIRST when a quick, reliable, encyclopedia-style overview of a
    person, place, concept, or event is needed, including its plain-text extract,
    internal link count, and canonical source URL.

    Args:
        query: The exact or approximate Wikipedia page title to look up
            (e.g. 'Artificial intelligence').
        lang: The Wikipedia language edition subdomain to query (default is 'en').

    Returns:
        Dictionary containing the page 'title', plain-text 'content', an
        'internal_links_count', and the 'source_url'. Returns a dictionary with
        a single 'error' key if no matching page was found or the request failed.
    """
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

    headers = {
        "User-Agent": "WebScopeExtract_CDAC_Project/1.0 (mahak@example.com)"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        pages = data.get("query", {}).get("pages", {})

        for page_id, page_info in pages.items():
            if page_id == "-1":
                return {"error": f"No Wikipedia page found for '{query}'"}

            return {
                "title": page_info.get("title"),
                "content": page_info.get("extract", "No content available."),
                "internal_links_count": len(page_info.get("links", [])),
                "source_url": f"https://{lang}.wikipedia.org/wiki/{query.replace(' ', '_')}"
            }

        return {"error": f"No Wikipedia page found for '{query}'"}

    except requests.exceptions.RequestException as e:
        return {"error": f"API Request failed: {str(e)}"}


#example
@tool
def search_youtube_transcripts(
    query: str, max_results: int = 3, languages: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Searches YouTube via the official Data API v3 and fetches each result's
    transcript. Use this tool FIRST when the request needs spoken content from
    videos (tutorials, talks, interviews, explainers) rather than just a video's
    title or description, since it returns the full transcript text alongside
    each result's metadata.

    Requires the YOUTUBE_API_KEY environment variable to be set with a valid
    YouTube Data API v3 key. Each call costs 100 quota units against that key's
    daily quota (default 10,000 units).

    Args:
        query: The search topic or keywords (e.g. 'how does photosynthesis work').
        max_results: Maximum number of videos to retrieve (default is 3).
        languages: Preferred transcript language codes in priority order
            (default is ['en']). Falls back to any available transcript if none
            of the preferred languages are found.

    Returns:
        List of dictionaries containing each video's 'title', 'url', 'channel',
        'published_at', 'description', and 'transcript' (full transcript text).
        A video with no usable transcript has 'transcript' set to None and a
        'transcript_error' explaining why. Returns a list with a single 'error'
        dictionary if the API key is missing or the search itself failed.
    """
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        return [{"error": "YOUTUBE_API_KEY environment variable is not set."}]

    if languages is None:
        languages = ["en"]

    youtube = build("youtube", "v3", developerKey=api_key)

    try:
        response = (
            youtube.search()
            .list(
                q=query,
                part="snippet",
                type="video",
                maxResults=max_results,
                order="relevance",
            )
            .execute()
        )
    except HttpError as e:
        return [{"error": f"YouTube API error: {str(e)}"}]

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
            "description": snippet.get("description"),
            "transcript": None,
            "transcript_error": None,
        }

        try:
            fetched_transcript = ytt_api.fetch(video_id, languages=languages)
        except NoTranscriptFound:
            try:
                transcript_list = ytt_api.list(video_id)
                transcript = next(iter(transcript_list))
                fetched_transcript = transcript.fetch()
            except Exception as e:
                fetched_transcript = None
                video_data["transcript_error"] = f"No transcript found in the requested language(s): {str(e)}"
        except TranscriptsDisabled:
            fetched_transcript = None
            video_data["transcript_error"] = "Transcripts are disabled for this video."
        except VideoUnavailable:
            fetched_transcript = None
            video_data["transcript_error"] = "Video is unavailable."
        except Exception as e:
            fetched_transcript = None
            video_data["transcript_error"] = f"Unexpected error: {str(e)}"

        if fetched_transcript:
            video_data["transcript"] = " ".join(snippet.text for snippet in fetched_transcript)

        results.append(video_data)

    return results


#example
@tool
def search_youtube_transcripts_no_key(
    query: str, max_results: int = 3, languages: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Searches YouTube via yt-dlp (no API key required) and fetches each result's
    transcript. Use this tool FIRST when YouTube video/transcript content is
    needed but no YOUTUBE_API_KEY is configured, or as a fallback when
    search_youtube_transcripts fails or is quota-limited. Returns less metadata
    than the official Data API (no publish date or description), but the
    transcript content itself is identical.

    Args:
        query: The search topic or keywords (e.g. 'how does photosynthesis work').
        max_results: Maximum number of videos to retrieve (default is 3).
        languages: Preferred transcript language codes in priority order
            (default is ['en']). Falls back to any available transcript if none
            of the preferred languages are found.

    Returns:
        List of dictionaries containing each video's 'title', 'url', 'channel',
        'duration' (seconds), and 'transcript' (full transcript text). A video
        with no usable transcript has 'transcript' set to None and a
        'transcript_error' explaining why. Returns a list with a single 'error'
        dictionary if the search itself failed.
    """
    if languages is None:
        languages = ["en"]

    search_query = f"ytsearch{max_results}:{query}"
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            entries = info.get("entries", []) if info else []
    except Exception as e:
        return [{"error": f"yt-dlp search failed: {str(e)}"}]

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
            "transcript_error": None,
        }

        try:
            fetched_transcript = ytt_api.fetch(video_id, languages=languages)
        except NoTranscriptFound:
            try:
                transcript_list = ytt_api.list(video_id)
                transcript = next(iter(transcript_list))
                fetched_transcript = transcript.fetch()
            except Exception as e:
                fetched_transcript = None
                video_data["transcript_error"] = f"No transcript found in the requested language(s): {str(e)}"
        except TranscriptsDisabled:
            fetched_transcript = None
            video_data["transcript_error"] = "Transcripts are disabled for this video."
        except VideoUnavailable:
            fetched_transcript = None
            video_data["transcript_error"] = "Video is unavailable."
        except Exception as e:
            fetched_transcript = None
            video_data["transcript_error"] = f"Unexpected error: {str(e)}"

        if fetched_transcript:
            video_data["transcript"] = " ".join(snippet.text for snippet in fetched_transcript)

        results.append(video_data)

    return results


#example
@tool
def search_web_news(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Searches the general web (including current news) via DuckDuckGo. Use this
    tool FIRST for fast-moving, current-events, or broad-topic queries where no
    single specialized source (arXiv, Wikipedia, YouTube) is a clear fit,
    requires no API key, and works well for recent headlines and breaking news.

    Args:
        query: The search topic or keywords, phrased as a natural search query
            (e.g. 'Microsoft layoffs Xbox restructure 2026').
        max_results: Maximum number of results to retrieve (default is 3).

    Returns:
        List of dictionaries containing each result's 'title', 'link', and
        'snippet' (short excerpt of the page content). Returns a list with a
        single 'error' dictionary if the search failed or returned nothing.
    """
    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
    except Exception as e:
        return [{"error": f"DuckDuckGo search failed: {str(e)}"}]

    if not raw_results:
        return [{"error": f"No results found for '{query}'"}]

    return [
        {
            "title": article.get("title", "No Title"),
            "link": article.get("href", "No Link"),
            "snippet": article.get("body", "No Snippet"),
        }
        for article in raw_results
    ]


#example
@tool
def find_site_feeds(domain: str) -> List[Dict[str, Any]]:
    """
    Discovers a website's syndication feeds (RSS/Atom/JSON Feed) by crawling
    the given domain. Use this tool FIRST when the goal is to monitor a site
    for new content over time (e.g. news updates, blog posts) rather than a
    one-off search, since a feed URL can be polled repeatedly without
    re-scraping the site.

    Args:
        domain: The site's domain or base URL to crawl for feeds
            (e.g. 'propublica.org').

    Returns:
        List of dictionaries containing each discovered feed's 'url', 'title',
        and 'content_type'. Returns a list with a single 'error' dictionary if
        no feeds were found or the crawl failed.
    """
    try:
        feeds = search_feeds(domain)
    except Exception as e:
        return [{"error": f"Feed discovery failed for '{domain}': {str(e)}"}]

    if not feeds:
        return [{"error": f"No syndication feeds (RSS/Atom/JSON) found for '{domain}'."}]

    return [
        {
            "url": str(feed.url),
            "title": feed.title if feed.title else "Untitled Feed",
            "content_type": feed.content_type if feed.content_type else "Unknown Format",
        }
        for feed in feeds
    ]


#example
@tool
def search_site_content(domain: str, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Searches for content within a specific website or subsection via a
    DuckDuckGo 'site:' search. Use this tool FIRST when the request needs
    results confined to one known domain or blog (e.g. a company's blog, docs
    site, or publication) rather than the open web, since restricting the
    search this way surfaces far more relevant, on-site results than a
    general web search filtered afterward.

    Args:
        domain: The domain or domain+path to restrict results to
            (e.g. 'scrapfly.io/blog').
        query: The search topic or keywords to look for within that domain
            (e.g. 'residential proxies bypass cloudflare').
        max_results: Maximum number of results to retrieve (default is 3).

    Returns:
        List of dictionaries containing each result's 'title', 'link', and
        'snippet' (short excerpt of the page content). Returns a list with a
        single 'error' dictionary if the search failed (e.g. anti-bot
        protection) or returned nothing.
    """
    dork_query = f"site:{domain} {query}"

    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(dork_query, max_results=max_results))
    except Exception as e:
        return [{"error": f"Search failed, possibly blocked by anti-bot protection: {str(e)}"}]

    if not raw_results:
        return [{"error": f"No results found on '{domain}' for '{query}'"}]

    return [
        {
            "title": result.get("title", "No Title"),
            "link": result.get("href", "No Link"),
            "snippet": result.get("body", "No Snippet"),
        }
        for result in raw_results
    ]
