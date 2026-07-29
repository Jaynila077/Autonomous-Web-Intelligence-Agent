from src.tools.search_tools import (
    search_arxiv,
    search_stackexchange,
    search_github_repos,
    search_mastodon,
    search_youtube,
    search_lemmy,
)
from src.tools.extractor_tools import (
    extract_pdf_with_pdfplumber,
    extract_github_readme,
    extract_youtube_transcript,
    extract_lemmy_post,
)

# The Master List of Tools given to the DeepAgent Orchestrator
AWIS_TOOL_REGISTRY = [
    # -- Search stage: cheap, broad discovery --
    search_arxiv,
    search_stackexchange,
    search_github_repos,
    search_mastodon,
    search_youtube,
    search_lemmy,

    # -- Extractor stage: expensive, targeted full-content fetch --
    extract_pdf_with_pdfplumber,
    extract_github_readme,
    extract_youtube_transcript,
    extract_lemmy_post,
]
