import uvicorn
from fastmcp import FastMCP

# Import underlying search and discovery functions from src/tools/
from src.tools.search_tools import (
    tavily_basic_search,
    tavily_advanced_research,
    search_with_exa,
    search_domain_with_dork,
)
from src.tools.academic_tools import search_arxiv_papers
from src.tools.wiki_tools import search_wikipedia_pages
from src.tools.health_tools import search_clinical_trials

mcp = FastMCP("AWIS Researcher MCP Server")

# Register Functions as MCP Tools
@mcp.tool()
def search_tavily(query: str, max_results: int = 5) -> str:
    """Perform a web search using Tavily API to find relevant URLs and initial facts."""
    return str(tavily_basic_search(query=query, max_results=max_results))

@mcp.tool()
def search_exa(query: str, num_results: int = 5) -> str:
    """Perform a neural/semantic search using Exa API."""
    return str(search_with_exa(query=query, num_results=num_results))

@mcp.tool()
def search_arxiv(query: str, max_results: int = 3) -> str:
    """Search academic research papers on arXiv."""
    return str(search_arxiv_papers(query=query, max_results=max_results))

@mcp.tool()
def search_wikipedia(query: str, limit: int = 5) -> str:
    """Search for relevant Wikipedia article titles and URLs."""
    return str(search_wikipedia_pages(query=query, limit=limit))

if __name__ == "__main__":
    # Run server via SSE / HTTP on port 8001
    mcp.run(transport="sse", port=8001)