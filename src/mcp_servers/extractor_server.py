from fastmcp import FastMCP

# Import underlying deep extraction tools
from src.tools.extractor_tools import (
    extract_article_text,
    extract_pdf_with_pdfplumber,
    save_intelligence_report as et_save_intelligence_report
)
from src.tools.wiki_tools import extract_wikipedia_summary as wt_extract_wikipedia_summary

mcp = FastMCP("AWIS Extractor MCP Server")

@mcp.tool()
def extract_webpage(url: str) -> str:
    """Scrape and extract main body content from a webpage URL."""
    return str(extract_article_text(url=url))

@mcp.tool()
def extract_pdf(pdf_url: str, max_pages: int = 10) -> str:
    """Parse and extract structured text from a PDF document URL or local path."""
    return str(extract_pdf_with_pdfplumber(pdf_url=pdf_url, max_pages=max_pages))

@mcp.tool()
def extract_wikipedia_summary(page_title: str) -> str:
    """Extract a clean text summary of a specific Wikipedia page."""
    return str(wt_extract_wikipedia_summary(page_title=page_title))

@mcp.tool()
def save_intelligence_report(query_title: str, report_content: str) -> str:
    """Save a generated intelligence report to the workspace."""
    return str(et_save_intelligence_report(query_title=query_title, report_content=report_content))

if __name__ == "__main__":
    # Run server via SSE / HTTP on port 8005
    mcp.run(transport="sse", port=8005)