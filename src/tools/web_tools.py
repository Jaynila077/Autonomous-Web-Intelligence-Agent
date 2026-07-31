import os
import random
import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from typing import List, Dict, Any, Optional

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
        # Ensure the domain has http/https for the requests library
        url = domain if domain.startswith("http") else f"https://{domain}"
        
        # Add a timeout so the agent doesn't hang forever on slow sites
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        feeds = []
        
        # Look for RSS/Atom link tags in the HTML head
        for link in soup.find_all('link', type=['application/rss+xml', 'application/atom+xml']):
            feed_url = link.get('href')
            if feed_url:
                # Handle relative URLs (e.g., href="/feed/")
                if feed_url.startswith('/'):
                    feed_url = f"{url.rstrip('/')}{feed_url}"
                    
                feeds.append({
                    "url": feed_url,
                    "title": link.get('title', "Untitled Feed"),
                    "content_type": link.get('type', "Unknown Format"),
                    "source_platform": "RSS/Atom Feed"
                })

        if not feeds:
            return [{"error": f"No syndication feeds found for '{domain}'."}]

        return feeds

    except Exception as e:
        return [{"error": f"Feed discovery failed: {str(e)}"}]