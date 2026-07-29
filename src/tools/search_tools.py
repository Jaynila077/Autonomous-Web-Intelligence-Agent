import io
import requests
import xml.etree.ElementTree as ET
from langchain_core.tools import tool
from typing import List, Dict, Any

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


import html
import os
import re


def _strip_html(s: str) -> str:
    text = re.sub(r"<[^>]+>", "", s or "")
    return html.unescape(text)


#example
@tool
def search_stackexchange(query: str, max_results: int = 10, site: str = "stackoverflow") -> List[Dict[str, Any]]:
    """
    Searches Stack Exchange (Stack Overflow by default) for questions and answers.
    Use this tool when researching a technical/programming problem, error message,
    or "how do I..." style question where practitioner Q&A is likely to have the answer.
    No API key is required for normal usage.

    Args:
        query: The search topic or technical keywords.
        max_results: Maximum number of questions to retrieve (default is 10).
        site: The Stack Exchange site to search (default is 'stackoverflow').

    Returns:
        List of dictionaries with question metadata, including full question body text.
    """
    url = "https://api.stackexchange.com/2.3/search/advanced"
    params = {
        "q": query,
        "site": site,
        "pagesize": max_results,
        "order": "desc",
        "sort": "relevance",
        "filter": "withbody",
    }
    api_key = os.getenv("STACKEXCHANGE_API_KEY")
    if api_key:
        params["key"] = api_key

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return [{"error": f"Failed to fetch Stack Exchange data: HTTP {response.status_code}"}]

        data = response.json()
        results = []
        for item in data.get("items", []):
            results.append({
                "title": _strip_html(item.get("title", "")),
                "author": item.get("owner", {}).get("display_name"),
                "created": str(item.get("creation_date")),
                "score": item.get("score"),
                "text": _strip_html(item.get("body", "")),
                "url": item.get("link", ""),
                "answer_count": item.get("answer_count"),
                "is_answered": item.get("is_answered"),
                "tags": item.get("tags"),
            })
        return results

    except Exception as e:
        return [{"error": f"Error querying Stack Exchange API: {str(e)}"}]


#example
@tool
def search_github_repos(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Searches GitHub for public repositories matching a query, sorted by stars.
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
    url = "https://api.github.com/search/repositories"
    params = {"q": query, "per_page": max_results, "sort": "stars", "order": "desc"}
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code != 200:
            return [{"error": f"Failed to fetch GitHub data: HTTP {response.status_code}"}]

        data = response.json()
        results = []
        for item in data.get("items", []):
            results.append({
                "full_name": item.get("full_name", ""),
                "author": item.get("owner", {}).get("login"),
                "created": item.get("created_at"),
                "stars": item.get("stargazers_count"),
                "language": item.get("language"),
                "forks": item.get("forks_count"),
                "text": item.get("description"),
                "url": item.get("html_url", ""),
            })
        return results

    except Exception as e:
        return [{"error": f"Error querying GitHub API: {str(e)}"}]


#example
@tool
def search_mastodon(query: str, max_results: int = 10, instance: str = "mastodon.social") -> List[Dict[str, Any]]:
    """
    Searches public statuses (posts) on a single Mastodon instance.
    Use this tool for open-source/tech-community sentiment or discussion on a topic.
    No API key required. Note: Mastodon is federated, so this only searches the given
    instance's index, not the whole fediverse.

    Args:
        query: The search topic or keywords.
        max_results: Maximum number of statuses to retrieve (default is 10).
        instance: The Mastodon instance host to search (default is 'mastodon.social').

    Returns:
        List of dictionaries with post metadata and full post text.
    """
    url = f"https://{instance}/api/v2/search"
    params = {"q": query, "type": "statuses", "limit": max_results}

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return [{"error": f"Failed to fetch Mastodon data: HTTP {response.status_code}"}]

        data = response.json()
        results = []
        for status in data.get("statuses", []):
            account = status.get("account", {})
            results.append({
                "title": _strip_html(status.get("content", ""))[:80],
                "author": account.get("acct"),
                "created": status.get("created_at"),
                "favourites": status.get("favourites_count"),
                "reblogs": status.get("reblogs_count"),
                "text": _strip_html(status.get("content", "")),
                "url": status.get("url", ""),
            })
        return results

    except Exception as e:
        return [{"error": f"Error querying Mastodon API: {str(e)}"}]


@tool
def search_youtube(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Searches YouTube for videos matching a query via the Data API v3.
    Use this tool when video content (talks, demos, interviews) is likely to be
    relevant. To read a video's full transcript, pass the returned 'video_id'
    into extract_youtube_transcript.
    REQUIRES the YOUTUBE_API_KEY environment variable to be set.

    Args:
        query: The search topic or keywords.
        max_results: Maximum number of videos to retrieve (default is 10).

    Returns:
        List of dictionaries with video metadata, including 'video_id' for use
        with extract_youtube_transcript.
    """
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        return [{"error": "YOUTUBE_API_KEY not set in environment."}]

    try:
        from googleapiclient.discovery import build
        youtube = build("youtube", "v3", developerKey=api_key)
        response = youtube.search().list(
            q=query, part="snippet", type="video", maxResults=max_results
        ).execute()
    except Exception as e:
        return [{"error": f"Error querying YouTube API: {str(e)}"}]

    results = []
    for item in response.get("items", []):
        vid = item["id"]["videoId"]
        snippet = item["snippet"]
        results.append({
            "title": snippet.get("title", ""),
            "author": snippet.get("channelTitle"),
            "created": snippet.get("publishedAt"),
            "text": snippet.get("description"),
            "video_id": vid,
            "url": f"https://www.youtube.com/watch?v={vid}",
        })
    return results


#example
@tool
def search_lemmy(query: str, max_results: int = 10, instance: str = "lemmy.world") -> List[Dict[str, Any]]:
    """
    Searches posts on a single Lemmy instance (a federated, Reddit-like platform).
    Use this tool as an additional public-discussion source alongside Reddit, especially
    for more technical/open-source-leaning communities. To read a post's comments,
    pass the returned 'post_id' into extract_lemmy_post, along with this same 'instance'
    value if you did not use the default.
    No API key required. Note: Lemmy is federated, so this only searches the given
    instance's index, not every Lemmy community.

    Args:
        query: The search topic or keywords.
        max_results: Maximum number of posts to retrieve (default is 10).
        instance: The Lemmy instance host to search (default is 'lemmy.world').

    Returns:
        List of dictionaries with post metadata, including 'post_id' for use
        with extract_lemmy_post.
    """
    url = f"https://{instance}/api/v3/search"
    params = {"q": query, "type_": "Posts", "sort": "TopAll", "limit": max_results}
    headers = {"User-Agent": "awis-osint-tool/1.0"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code != 200:
            return [{"error": f"Failed to fetch Lemmy data: HTTP {response.status_code}"}]

        data = response.json()
        results = []
        for item in data.get("posts", []):
            post = item.get("post", {})
            counts = item.get("counts", {})
            creator = item.get("creator", {})
            community = item.get("community", {})
            results.append({
                "title": post.get("name", ""),
                "author": creator.get("name"),
                "created": post.get("published"),
                "score": counts.get("score"),
                "community": community.get("name"),
                "num_comments": counts.get("comments"),
                "text": post.get("body"),
                "post_id": post.get("id"),
                "url": post.get("ap_id", ""),
            })
        return results

    except Exception as e:
        return [{"error": f"Error querying Lemmy API: {str(e)}"}]
