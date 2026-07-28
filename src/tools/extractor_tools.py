from langchain_core.tools import tool

#example 
@tool
def extract_page_markdown(url: str) -> str:
    """
    Scrapes a webpage URL and converts the body text into clean Markdown.
    Use this ONLY when you have a specific webpage URL you need to read in detail.
    """
    # Placeholder: Connect Jina Reader API (https://r.jina.ai/<url>) or Trafilatura
    return f"# Extracted Content from {url}\n\nThis is clean markdown text retrieved from the webpage."
