from fastmcp import FastMCP
from typing import Optional, List

# Import underlying media and social tools
from src.tools.media_tools import (
    search_youtube_transcripts as mt_search_youtube_transcripts,
    search_youtube_transcripts_no_key as mt_search_youtube_transcripts_no_key
)
from src.tools.social_tools import (
    search_mastodon as st_search_mastodon,
    search_lemmy as st_search_lemmy
)

mcp = FastMCP("AWIS Media & Social MCP Server")

@mcp.tool()
def search_youtube_transcripts(query: str, max_results: int = 3, languages: Optional[List[str]] = None) -> str:
    """Searches YouTube via official Data API v3 and fetches each result's transcript."""
    return str(mt_search_youtube_transcripts(query=query, max_results=max_results, languages=languages))

@mcp.tool()
def search_youtube_transcripts_no_key(query: str, max_results: int = 3, languages: Optional[List[str]] = None) -> str:
    """Searches YouTube via yt-dlp (no API key required) and fetches video transcripts."""
    return str(mt_search_youtube_transcripts_no_key(query=query, max_results=max_results, languages=languages))

@mcp.tool()
def search_mastodon(query: str, max_results: int = 5, instance: str = "mastodon.social") -> str:
    """Searches Mastodon for posts and discussions."""
    return str(st_search_mastodon(query=query, max_results=max_results, instance=instance))

@mcp.tool()
def search_lemmy(query: str, max_results: int = 10, instance: str = "lemmy.world") -> str:
    """Searches Lemmy for community posts and discussions."""
    return str(st_search_lemmy(query=query, max_results=max_results, instance=instance))

if __name__ == "__main__":
    # Run server via SSE / HTTP on port 8004
    mcp.run(transport="sse", port=8004)