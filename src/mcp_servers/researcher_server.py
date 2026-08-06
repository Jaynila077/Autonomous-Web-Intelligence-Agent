from fastmcp import FastMCP

# Import underlying search and discovery functions from src/tools/
from src.tools.web_tools import (
    search_tavily as wt_search_tavily,
    search_web_news as wt_search_web_news,
    search_exa_semantic as wt_search_exa_semantic,
    find_working_searxng as wt_find_working_searxng,
    search_site_content as wt_search_site_content,
    find_site_feeds as wt_find_site_feeds,
    fetch_wiki_data as wt_fetch_wiki_data,
)
from src.tools.news_tools import monitor_rss_feed as nt_monitor_rss_feed

mcp = FastMCP("AWIS Researcher MCP Server")

# Register Functions as MCP Tools
@mcp.tool()
def search_tavily(query: str, max_results: int = 3, search_depth: str = "basic", topic: str = "general", include_answer: bool = False) -> str:
    """Runs a structured web search via Tavily API with relevance scoring (Cached 24h)."""
    return str(wt_search_tavily(query=query, max_results=max_results, search_depth=search_depth, topic=topic, include_answer=include_answer))

@mcp.tool()
def search_web_news(query: str, max_results: int = 3) -> str:
    """Searches the general web and live headlines via DuckDuckGo."""
    return str(wt_search_web_news(query=query, max_results=max_results))

@mcp.tool()
def search_exa_semantic(semantic_query: str, max_links: int = 2) -> str:
    """Runs a neural/semantic web search via Exa API and returns extracted highlights."""
    return str(wt_search_exa_semantic(semantic_query=semantic_query, max_links=max_links))

@mcp.tool()
def find_working_searxng(min_uptime_pct: float = 90.0, max_instances: int = 5) -> str:
    """Discovers currently reachable, publicly-hosted SearXNG instances."""
    return str(wt_find_working_searxng(min_uptime_pct=min_uptime_pct, max_instances=max_instances))

@mcp.tool()
def search_site_content(domain: str, query: str, max_results: int = 3) -> str:
    """Searches for content within a specific domain via a 'site:' dork query."""
    return str(wt_search_site_content(domain=domain, query=query, max_results=max_results))

@mcp.tool()
def find_site_feeds(domain: str) -> str:
    """Discovers a website's RSS/Atom/JSON syndication feeds."""
    return str(wt_find_site_feeds(domain=domain))

@mcp.tool()
def fetch_wiki_data(query: str, lang: str = "en") -> str:
    """Fetches a structured summary of a Wikipedia article via MediaWiki API (Cached 24h)."""
    return str(wt_fetch_wiki_data(query=query, lang=lang))

@mcp.tool()
def monitor_rss_feed(feed_url: str, max_articles: int = 5) -> str:
    """Monitors and extracts latest articles from an RSS/Atom feed."""
    return str(nt_monitor_rss_feed(feed_url=feed_url, max_articles=max_articles))

if __name__ == "__main__":
    # Run server via SSE / HTTP on port 8001
    mcp.run(transport="sse", port=8001)