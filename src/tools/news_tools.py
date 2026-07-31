import feedparser
from ddgs import DDGS
from langchain_core.tools import tool
from typing import List, Dict, Any

@tool
def search_news_duckduckgo(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Searches the general web and news using DuckDuckGo to find recent articles, 
    press releases, or updates on a specific topic.
    
    Use this tool when you need to actively hunt for the latest information, company 
    announcements, or current events based on a keyword search. This tool returns 
    metadata and URLs, but DOES NOT extract the full article text.
    
    Args:
        query (str): The specific search string, keywords, or news topic (e.g., 'Microsoft Xbox restructuring').
        max_results (int, optional): The maximum number of search results to retrieve. Defaults to 3.
        
    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing the search results. Each dictionary contains:
            - title (str): The search engine title of the article/page.
            - url (str): The direct hyperlink to the page (to be passed to a web extractor tool).
            - snippet (str): A short text preview or summary provided by the search engine.
            
        If no results are found, returns an empty list. If an error occurs, returns a list containing a single dictionary with an 'error' key.
    """
    extracted_results = []
    
    try:
        with DDGS() as ddgs:
            # We use .text() for general web/news search
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


@tool
def monitor_rss_feed(feed_url: str, max_articles: int = 5) -> List[Dict[str, Any]]:
    """
    Scans and parses a specific RSS feed URL to fetch the most recently published articles.
    
    Use this tool when you know the exact RSS feed of a news organization, blog, or 
    website (e.g., 'http://feeds.bbci.co.uk/news/technology/rss.xml') and want to 
    monitor it for their latest posts. This tool ONLY retrieves article metadata.
    
    Args:
        feed_url (str): The direct URL to the RSS XML feed.
        max_articles (int, optional): The maximum number of recent articles to retrieve. Defaults to 5.
        
    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing the feed articles. Each dictionary contains:
            - title (str): The headline of the published article.
            - url (str): The direct hyperlink to the full article.
            - published (str): The publication timestamp/date.
            
        If the feed is invalid or cannot be parsed, returns a list containing a single dictionary with an 'error' key.
    """
    try:
        feed = feedparser.parse(feed_url)
        
        # 'bozo' is feedparser's flag for a malformed or invalid feed
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