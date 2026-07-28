from src.tools.search_tools import search_news_and_web, search_academic_arxiv
from src.tools.extractor_tools import extract_page_markdown

# The Master List of Tools given to the DeepAgent Orchestrator
AWIS_TOOL_REGISTRY = [
    search_news_and_web,
    search_academic_arxiv,
    extract_page_markdown
]
