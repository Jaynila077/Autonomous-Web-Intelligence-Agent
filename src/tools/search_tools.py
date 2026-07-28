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




import base64
import html
import io
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import feedparser
import pdfplumber
import requests
import trafilatura
from ddgs import DDGS
from dotenv import load_dotenv
from exa_py import Exa
from langchain_core.tools import tool
from tavily import TavilyClient
from usp.tree import sitemap_tree_for_homepage



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




# ---------------------------------------------------------------------------
# Clinical trials (health/clinical_scraper.py)
# ---------------------------------------------------------------------------

@tool
def search_clinical_trials(search_term: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Searches ClinicalTrials.gov for studies matching a medical/clinical term.
    Use this tool FIRST when a request needs information on active, completed,
    or recruiting clinical trials for a drug, condition, or intervention,
    since it queries the official registry directly rather than a general
    web search.

    Args:
        search_term: The condition, drug, or intervention to search for
            (e.g. 'mRNA vaccine').
        limit: Maximum number of studies to retrieve (default is 5).

    Returns:
        List of dictionaries containing each study's 'NCT_ID', 'Title',
        'Status', and 'Summary'. Returns a list with a single 'error'
        dictionary if the request failed.
    """
    url = "https://clinicaltrials.gov/api/v2/studies"
    params = {"query.term": search_term, "pageSize": limit, "format": "json"}

    try:
        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        return [{"error": f"Error fetching data: {str(e)}"}]

    extracted_trials = []
    for study in data.get("studies", []):
        protocol = study.get("protocolSection", {})
        identification = protocol.get("identificationModule", {})
        status = protocol.get("statusModule", {})
        description = protocol.get("descriptionModule", {})

        extracted_trials.append({
            "NCT_ID": identification.get("nctId", "N/A"),
            "Title": identification.get("briefTitle", "N/A"),
            "Status": status.get("overallStatus", "N/A"),
            "Summary": description.get("briefSummary", "No summary provided."),
        })

    return extracted_trials






# ---------------------------------------------------------------------------
# Exa semantic search (blog/test_exa.py)
# ---------------------------------------------------------------------------

@tool
def search_exa_semantic(semantic_query: str, max_links: int = 2) -> List[Dict[str, Any]]:
    """
    Runs a neural/semantic web search via the Exa API and returns extracted
    highlight snippets per result. Use this tool FIRST when a request is
    phrased as a rich, descriptive prompt (rather than a short keyword
    query) and needs conceptually-matched pages rather than plain keyword
    matches -- Exa's embeddings-based search is stronger than a keyword
    engine for this kind of query.

    Requires the EXA_API_KEY environment variable to be set.

    Args:
        semantic_query: A descriptive natural-language query or prompt
            (e.g. 'a highly detailed, technical engineering blog post about
            bypassing Cloudflare for web scraping').
        max_links: Maximum number of results to retrieve (default is 2).

    Returns:
        List of dictionaries containing each result's 'title', 'url', and
        'highlights' (list of extracted highlight strings). Returns a list
        with a single 'error' dictionary if the API key is missing or the
        call failed.
    """
    api_key = os.environ.get("EXA_API_KEY")
    if not api_key:
        return [{"error": "EXA_API_KEY environment variable is not set."}]

    try:
        exa = Exa(api_key=api_key)
        response = exa.search(
            semantic_query,
            type="auto",
            num_results=max_links,
            contents={"highlights": True},
        )
        results = response.results
    except Exception as e:
        return [{"error": f"Exa API call failed: {str(e)}"}]

    if not results:
        return [{"error": "No semantic matches found."}]

    return [
        {
            "title": article.title,
            "url": article.url,
            "highlights": [h.replace("\n", " ").strip() for h in article.highlights] if article.highlights else [],
        }
        for article in results
    ]


# ---------------------------------------------------------------------------
# Tavily (Tavily/main.py)
# ---------------------------------------------------------------------------

def _get_tavily_client() -> Optional[TavilyClient]:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return None
    return TavilyClient(api_key=api_key)


@tool
def search_tavily(
    query: str,
    max_results: int = 3,
    search_depth: str = "basic",
    topic: str = "general",
    include_answer: bool = False,
    include_domains: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Runs a structured web search via the Tavily API, with support for
    deeper crawling, topic filtering, domain allowlisting, and an optional
    AI-synthesized summary answer. Use this tool FIRST when a request needs
    higher-quality, relevance-scored results than a plain search engine,
    especially for news/finance topics or when restricting to trusted
    domains (e.g. 'nature.com', 'sciencedaily.com').

    Requires the TAVILY_API_KEY environment variable to be set.

    Args:
        query: The search query.
        max_results: Maximum number of results to retrieve (default is 3).
        search_depth: 'basic' (fast) or 'advanced' (deeper, higher quality,
            default is 'basic').
        topic: 'general', 'news', or 'finance' (default is 'general').
        include_answer: Whether to also generate a synthesized summary
            answer inside the response (default is False).
        include_domains: Optional list of domains to restrict results to.

    Returns:
        Dictionary containing 'answer' (synthesized summary, or None if
        include_answer is False) and 'results' (list of dictionaries with
        'title', 'url', 'score', and 'content'). Returns a dictionary with
        a single 'error' key if the API key is missing or the call failed.
    """
    client = _get_tavily_client()
    if client is None:
        return {"error": "TAVILY_API_KEY environment variable is not set."}

    try:
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth=search_depth,
            topic=topic,
            include_answer=include_answer,
            include_domains=include_domains,
        )
    except Exception as e:
        return {"error": f"Tavily search failed: {str(e)}"}

    return {
        "answer": response.get("answer"),
        "results": [
            {
                "title": r.get("title"),
                "url": r.get("url"),
                "score": r.get("score"),
                "content": r.get("content"),
            }
            for r in response.get("results", [])
        ],
    }





# ---------------------------------------------------------------------------
# OSINT multi-source adapters (osint_pipeline/adapters.py) --
# each platform exposed as its own tool, matching the file's per-source design.
# ---------------------------------------------------------------------------

def _strip_html_tags(raw: str) -> str:
    text = re.sub(r"<script.*?</script>", "", raw, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


@tool
def search_stackexchange(query: str, site: str = "stackoverflow", limit: int = 10) -> List[Dict[str, Any]]:
    """
    Searches a Stack Exchange site (e.g. Stack Overflow) for questions
    matching a query, including full question body text. Use this tool
    FIRST for technical/programming questions where community Q&A content
    (with an answered/vote-count relevance signal) is more useful than a
    general web search.

    Optional STACKEXCHANGE_API_KEY environment variable raises the request
    quota but is not required for low-volume use.

    Args:
        query: The search query.
        site: The Stack Exchange site to search (default is 'stackoverflow').
        limit: Maximum number of questions to retrieve (default is 10).

    Returns:
        List of dictionaries containing each question's 'title', 'url',
        'author', 'created_at', 'score', 'body', 'answer_count',
        'is_answered', and 'tags'. Returns a list with a single 'error'
        dictionary if the request failed.
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
    except Exception as e:
        return [{"error": str(e)}]

    return [
        {
            "title": _strip_html_tags(item.get("title", "")),
            "url": item.get("link", ""),
            "author": item.get("owner", {}).get("display_name"),
            "created_at": str(item.get("creation_date")),
            "score": item.get("score"),
            "body": _strip_html_tags(item.get("body", "")),
            "answer_count": item.get("answer_count"),
            "is_answered": item.get("is_answered"),
            "tags": item.get("tags"),
        }
        for item in data.get("items", [])
    ]


@tool
def search_github_repos(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Searches GitHub repositories matching a query, sorted by star count.
    Use this tool FIRST when a request needs open-source projects, tools,
    or code examples related to a topic.

    Optional GITHUB_TOKEN environment variable raises the unauthenticated
    rate limit but is not required.

    Args:
        query: The search query (supports GitHub search qualifiers).
        limit: Maximum number of repositories to retrieve (default is 10).

    Returns:
        List of dictionaries containing each repo's 'full_name', 'url',
        'owner', 'created_at', 'stars', 'description', 'language', and
        'forks'. Returns a list with a single 'error' dictionary if the
        request failed.
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
    except Exception as e:
        return [{"error": str(e)}]

    return [
        {
            "full_name": item.get("full_name", ""),
            "url": item.get("html_url", ""),
            "owner": item.get("owner", {}).get("login"),
            "created_at": item.get("created_at"),
            "stars": item.get("stargazers_count"),
            "description": item.get("description"),
            "language": item.get("language"),
            "forks": item.get("forks_count"),
        }
        for item in data.get("items", [])
    ]


@tool
def search_mastodon(query: str, instance: str = "mastodon.social", limit: int = 10) -> List[Dict[str, Any]]:
    """
    Searches a single Mastodon instance's public statuses for a query. Use
    this tool FIRST for Mastodon/fediverse chatter on a topic. Note that
    federated search is instance-scoped -- this covers what the chosen
    instance knows about, not the entire fediverse.

    Args:
        query: The search query.
        instance: The Mastodon instance hostname to search (default is
            'mastodon.social').
        limit: Maximum number of statuses to retrieve (default is 10).

    Returns:
        List of dictionaries containing each status's 'preview' (first 80
        chars of stripped content), 'url', 'author', 'created_at',
        'favourites', 'content' (full stripped text), and 'reblogs'.
        Returns a list with a single 'error' dictionary if the request
        failed.
    """
    try:
        resp = requests.get(
            f"https://{instance}/api/v2/search",
            params={"q": query, "type": "statuses", "limit": limit},
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return [{"error": str(e)}]

    results = []
    for status in data.get("statuses", []):
        content = _strip_html_tags(status.get("content", ""))
        account = status.get("account", {})
        results.append({
            "preview": content[:80],
            "url": status.get("url", ""),
            "author": account.get("acct"),
            "created_at": status.get("created_at"),
            "favourites": status.get("favourites_count"),
            "content": content,
            "reblogs": status.get("reblogs_count"),
        })

    return results


@tool
def search_reddit(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Searches Reddit for submissions matching a query, via the public
    `.json` endpoint. Use this tool FIRST for Reddit discussion/opinion on
    a topic. Note that Reddit's public endpoint intermittently 403s
    unauthenticated traffic; if that happens, treat this source as
    temporarily unavailable rather than retrying repeatedly.

    Args:
        query: The search query.
        limit: Maximum number of submissions to retrieve (default is 10).

    Returns:
        List of dictionaries containing each submission's 'title', 'url',
        'author', 'created_utc', 'score', 'selftext', 'subreddit', and
        'num_comments'. Returns a list with a single 'error' dictionary if
        the request failed (e.g. blocked with a 403).
    """
    headers = {"User-Agent": "osint-search-tools/0.1"}
    try:
        resp = requests.get(
            "https://www.reddit.com/search.json",
            params={"q": query, "limit": limit, "sort": "relevance"},
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return [{"error": str(e)}]

    results = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        results.append({
            "title": d.get("title", ""),
            "url": "https://www.reddit.com" + d.get("permalink", ""),
            "author": d.get("author"),
            "created_utc": str(d.get("created_utc")),
            "score": d.get("score"),
            "selftext": d.get("selftext"),
            "subreddit": d.get("subreddit"),
            "num_comments": d.get("num_comments"),
        })

    return results


@tool
def search_lemmy(query: str, instance: str = "lemmy.world", limit: int = 10) -> List[Dict[str, Any]]:
    """
    Searches a single Lemmy instance for posts matching a query. Use this
    tool FIRST for Lemmy/fediverse discussion on a topic, especially
    tech/open-source/Linux communities where Lemmy activity is dense. Same
    federation caveat as Mastodon: one instance's search isn't all of
    Lemmy.

    Args:
        query: The search query.
        instance: The Lemmy instance hostname to search (default is
            'lemmy.world').
        limit: Maximum number of posts to retrieve (default is 10).

    Returns:
        List of dictionaries containing each post's 'title', 'url'
        (ActivityPub canonical link), 'author', 'created_at', 'score',
        'body', 'community', and 'num_comments'. Returns a list with a
        single 'error' dictionary if the request failed.
    """
    headers = {"User-Agent": "osint-search-tools/0.1"}
    try:
        resp = requests.get(
            f"https://{instance}/api/v3/search",
            params={"q": query, "type_": "Posts", "sort": "TopAll", "limit": limit},
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return [{"error": str(e)}]

    results = []
    for item in data.get("posts", []):
        post = item.get("post", {})
        counts = item.get("counts", {})
        creator = item.get("creator", {})
        community = item.get("community", {})
        results.append({
            "title": post.get("name", ""),
            "url": post.get("ap_id", ""),
            "author": creator.get("name"),
            "created_at": post.get("published"),
            "score": counts.get("score"),
            "body": post.get("body"),
            "community": community.get("name"),
            "num_comments": counts.get("comments"),
        })

    return results


@tool
def search_tumblr(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Searches Tumblr by tag (Tumblr's free API has no full-text search, so
    the query is collapsed to a single tag). Use this tool FIRST for
    Tumblr fandom/creative-community content on a topic that maps
    reasonably to a single tag word.

    Requires the TUMBLR_API_KEY environment variable to be set.

    Args:
        query: The search topic; spaces are stripped to form a tag (e.g.
            'web scraping' -> 'webscraping').
        limit: Maximum number of posts to retrieve (default is 10).

    Returns:
        List of dictionaries containing each post's 'title' (first 80
        chars of stripped summary/caption), 'url', 'author' (blog name),
        'created_at', 'notes', 'tags', and 'type'. Returns a list with a
        single 'error' dictionary if the API key is missing or the request
        failed.
    """
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
        data = resp.json()
    except Exception as e:
        return [{"error": str(e)}]

    results = []
    for post in data.get("response", []):
        body = post.get("summary") or post.get("caption") or ""
        clean_body = _strip_html_tags(body)
        results.append({
            "title": clean_body[:80] or "(untitled post)",
            "url": post.get("post_url", ""),
            "author": post.get("blog_name"),
            "created_at": post.get("date"),
            "notes": post.get("note_count"),
            "tags": post.get("tags"),
            "type": post.get("type"),
        })

    return results


@tool
def search_vk(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Searches VKontakte (VK) newsfeed posts matching a query. Use this tool
    FIRST when Russian/Eastern European language or geographic coverage is
    needed, which most other configured sources lack.

    Requires the VK_ACCESS_TOKEN environment variable to be set (register
    an app at vk.com/apps?act=manage and generate a token with the 'wall'
    scope via the Implicit Flow).

    Args:
        query: The search query.
        limit: Maximum number of posts to retrieve (default is 10).

    Returns:
        List of dictionaries containing each post's 'title' (first 80
        chars of text), 'url', 'author' (owner id), 'created_at', 'likes',
        'reposts', and 'comments'. Returns a list with a single 'error'
        dictionary if the token is missing, the request failed, or the VK
        API returned an error.
    """
    access_token = os.environ.get("VK_ACCESS_TOKEN")
    if not access_token:
        return [{"error": "VK_ACCESS_TOKEN environment variable is not set."}]

    params = {"q": query, "count": limit, "access_token": access_token, "v": "5.199"}

    try:
        resp = requests.get("https://api.vk.com/method/newsfeed.search", params=params, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return [{"error": str(e)}]

    if "error" in data:
        err = data["error"]
        return [{"error": f"VK API error {err.get('error_code')}: {err.get('error_msg')}"}]

    results = []
    for item in data.get("response", {}).get("items", []):
        owner_id = item.get("owner_id")
        post_id = item.get("id")
        text = item.get("text", "")
        results.append({
            "title": text[:80] if text else "(no text)",
            "url": f"https://vk.com/wall{owner_id}_{post_id}",
            "author": str(owner_id),
            "created_at": str(item.get("date")),
            "likes": item.get("likes", {}).get("count"),
            "reposts": item.get("reposts", {}).get("count"),
            "comments": item.get("comments", {}).get("count"),
        })

    return results


@tool
def search_bluesky(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Searches Bluesky (AT Protocol) posts matching a query via the public
    endpoint, falling back to an authenticated session if credentials are
    set and the public endpoint 403s (a known intermittent issue with
    Bluesky's public infra). Use this tool FIRST for Bluesky chatter on a
    topic.

    Optional BLUESKY_HANDLE and BLUESKY_APP_PASSWORD environment variables
    (generate an app password at bsky.app -> Settings -> App Passwords,
    NOT your main account password) enable the authenticated fallback.

    Args:
        query: The search query.
        limit: Maximum number of posts to retrieve (default is 10).

    Returns:
        List of dictionaries containing each post's 'title' (first 80
        chars of text), 'url', 'author' (handle), 'created_at', 'likes',
        'reposts', 'replies', and 'text'. Returns a list with a single
        'error' dictionary if both the public and authenticated attempts
        failed.
    """
    headers = {"User-Agent": "osint-search-tools/0.1"}
    params = {"q": query, "limit": limit}

    try:
        resp = requests.get(
            "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts",
            params=params, headers=headers, timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as public_err:
        handle = os.environ.get("BLUESKY_HANDLE")
        app_password = os.environ.get("BLUESKY_APP_PASSWORD")
        if not (handle and app_password):
            return [{"error": f"public endpoint failed ({str(public_err)}) and no BLUESKY_HANDLE/APP_PASSWORD set for authed fallback"}]

        try:
            session_resp = requests.post(
                "https://bsky.social/xrpc/com.atproto.server.createSession",
                json={"identifier": handle, "password": app_password},
                timeout=DEFAULT_TIMEOUT,
            )
            session_resp.raise_for_status()
            token = session_resp.json().get("accessJwt")

            auth_headers = {**headers, "Authorization": f"Bearer {token}"}
            resp = requests.get(
                "https://bsky.social/xrpc/app.bsky.feed.searchPosts",
                params=params, headers=auth_headers, timeout=DEFAULT_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as authed_err:
            return [{"error": str(authed_err)}]

    results = []
    for post in data.get("posts", []):
        author = post.get("author", {})
        record = post.get("record", {})
        handle = author.get("handle", "")
        uri = post.get("uri", "")
        rkey = uri.rsplit("/", 1)[-1] if uri else ""
        text = record.get("text", "")

        results.append({
            "title": text[:80] if text else "(no text)",
            "url": f"https://bsky.app/profile/{handle}/post/{rkey}" if handle and rkey else "",
            "author": handle,
            "created_at": record.get("createdAt"),
            "likes": post.get("likeCount"),
            "reposts": post.get("repostCount"),
            "replies": post.get("replyCount"),
            "text": text,
        })

    return results
