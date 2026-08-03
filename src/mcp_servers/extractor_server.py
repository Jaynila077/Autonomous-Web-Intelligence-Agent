from fastmcp import FastMCP

# Import underlying deep extraction tools
from src.tools.extractor_tools import (
    extract_article_text,
    extract_pdf_with_pdfplumber,
)
from src.tools.youtube_tools import extract_youtube_transcript
from src.tools.wiki_tools import extract_wikipedia_summary

mcp = FastMCP("AWIS Extractor MCP Server")

@mcp.tool()
def extract_webpage(url: str) -> str:
    """Scrape and extract main body content from a webpage URL."""
    return str(extract_article_text(url=url))

@mcp.tool()
def extract_pdf(pdf_url_or_path: str) -> str:
    """Parse and extract structured text from a PDF document URL or local path."""
    return str(extract_pdf_with_pdfplumber(pdf_url_or_path=pdf_url_or_path))

@mcp.tool()
def extract_youtube(video_url: str) -> str:
    """Fetch transcripts and captions from a YouTube video URL."""
    return str(extract_youtube_transcript(video_url=video_url))

if __name__ == "__main__":
    # Run server via SSE / HTTP on port 8002
    mcp.run(transport="sse", port=8002)