import feedparser
from ddgs import DDGS
from langchain_core.tools import tool
from typing import List, Dict, Any

@tool
def search_news_duckduckgo(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Searches the general web and news using DuckDuckGo to find recent articles.
    """
    extracted_results = []
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            if not results:
                return []
            for result in results:
                extracted_results.append({
                    "title": result.get('title', 'No Title'),
                    "url": result.get('href', 'No Link'),
                    "snippet": result.get('body', 'No Snippet')
                })
            return extracted_results
    except Exception as e:
        return [{"error": f"Search failed. Details: {str(e)}"}]

def monitor_rss_feed(feed_url: str, max_articles: int = 5) -> List[Dict[str, Any]]:
    """
    Scans and parses a specific RSS feed URL to fetch the most recently published articles.
    """
    try:
        feed = feedparser.parse(feed_url)
        if getattr(feed, 'bozo', False):
            return [{"error": f"Could not parse the feed. Check if the URL is a valid RSS feed: {feed_url}"}]
        articles = feed.entries[:max_articles]
        if not articles:
            return []
        extracted_articles = []
        for article in articles:
            extracted_articles.append({
                "title": article.get('title', 'No Title'),
                "url": article.get('link', 'No Link'),
                "published": article.get('published', 'Unknown Time')
            })
        return extracted_articles
    except Exception as e:
        return [{"error": f"An error occurred while parsing the RSS feed: {str(e)}"}]