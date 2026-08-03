from fastmcp import FastMCP

# Import underlying academic search tools
from src.tools.academic_tools import (
    search_arxiv as at_search_arxiv,
    search_clinical_trials as at_search_clinical_trials
)

mcp = FastMCP("AWIS Academic MCP Server")

@mcp.tool()
def search_arxiv(query: str, max_results: int = 3) -> str:
    """Search academic research papers on arXiv."""
    return str(at_search_arxiv(query=query, max_results=max_results))

@mcp.tool()
def search_clinical_trials(search_term: str, limit: int = 5) -> str:
    """Search for clinical trials via ClinicalTrials.gov."""
    return str(at_search_clinical_trials(search_term=search_term, limit=limit))

if __name__ == "__main__":
    # Run server via SSE / HTTP on port 8002
    mcp.run(transport="sse", port=8002)