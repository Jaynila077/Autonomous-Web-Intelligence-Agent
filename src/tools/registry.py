from src.tools.search_tools import search_arxiv
from src.tools.extractor_tools import extract_pdf_with_pdfplumber

# The Master List of Tools given to the DeepAgent Orchestrator
AWIS_TOOL_REGISTRY = [
    search_arxiv,
    extract_pdf_with_pdfplumber
]
