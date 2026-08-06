from fastmcp import FastMCP

# Import underlying developer tools
from src.tools.dev_tools import (
    search_github_repos as dt_search_github_repos,
    search_stackexchange as dt_search_stackexchange
)

mcp = FastMCP("AWIS Developer MCP Server")

@mcp.tool()
def search_github_repos(query: str, limit: int = 5) -> str:
    """Search GitHub for repositories matching the query."""
    return str(dt_search_github_repos(query=query, limit=limit))

@mcp.tool()
def search_stackexchange(query: str, max_results: int = 10, site: str = "stackoverflow") -> str:
    """Search StackExchange sites (e.g., stackoverflow) for answers."""
    return str(dt_search_stackexchange(query=query, max_results=max_results, site=site))

if __name__ == "__main__":
    # Run server via SSE / HTTP on port 8003
    mcp.run(transport="sse", port=8003)