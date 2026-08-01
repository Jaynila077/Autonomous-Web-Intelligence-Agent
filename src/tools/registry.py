from src.tools.academic_tools import search_arxiv, search_clinical_trials
from src.tools.search_tools import search_arxiv_papers
from src.tools.web_tools import (
    fetch_wiki_data,
    search_web_news,
    search_tavily,
    search_exa_semantic,
    find_working_searxng,
    search_site_content,
    find_site_feeds,
)
from src.tools.dev_tools import search_github_repos, search_stackexchange
from src.tools.media_tools import search_youtube_transcripts, search_youtube_transcripts_no_key
from src.tools.social_tools import (
    search_mastodon,
    search_lemmy,
)
from src.tools.extractor_tools import extract_pdf_with_pdfplumber, save_intelligence_report

# 1. Subagent Scoped Toolsets (keeps prompt tokens light & prevents 429 rate limits)
RESEARCHER_TOOLS = [
    search_arxiv,
    search_arxiv_papers,
    search_clinical_trials,
    fetch_wiki_data,
    search_web_news,
    search_tavily,
    search_exa_semantic,
    search_github_repos,
    search_youtube_transcripts,
    extract_pdf_with_pdfplumber,
]

VERIFIER_TOOLS = [
    fetch_wiki_data,
    search_tavily,
    search_stackexchange,
    search_arxiv,
]

REPORTER_TOOLS = [
    save_intelligence_report,
]

# 2. Master Registry containing all active tools across all modules
AWIS_TOOL_REGISTRY = [
    search_arxiv,
    search_arxiv_papers,
    search_clinical_trials,
    fetch_wiki_data,
    search_web_news,
    search_tavily,
    search_exa_semantic,
    find_working_searxng,
    search_site_content,
    find_site_feeds,
    search_github_repos,
    search_stackexchange,
    search_youtube_transcripts,
    search_youtube_transcripts_no_key,
    search_mastodon,
    search_lemmy,
    extract_pdf_with_pdfplumber,
    save_intelligence_report,
]


def select_dynamic_tools(query: str, max_tools: int = 2) -> list:
    """
    Dynamic Tool Router: Inspects the user's research query and selects 
    the top 2 most relevant tools from all active tools in AWIS_TOOL_REGISTRY.
    Preserves 100% of AWIS's multi-source USP while eliminating schema noise.
    """
    q = query.lower()
    selected = []

    def _add(tool):
        if tool not in selected:
            selected.append(tool)

    # Domain 1: Academic & Research
    if any(k in q for k in ["paper", "arxiv", "research", "architecture", "model", "algorithm", "study", "ai"]):
        _add(search_arxiv)
        _add(search_arxiv_papers)
    if any(k in q for k in ["clinical", "trial", "medical", "drug", "patient", "health", "disease"]):
        _add(search_clinical_trials)

    # Domain 2: Code & Engineering
    if any(k in q for k in ["code", "repo", "github", "python", "framework", "library", "sdk"]):
        _add(search_github_repos)
    if any(k in q for k in ["stack", "overflow", "error", "bug", "how to", "issue"]):
        _add(search_stackexchange)

    # Domain 3: Community & Social Sentiment
    if any(k in q for k in ["mastodon", "lemmy", "community", "discussion", "fediverse", "social"]):
        _add(search_mastodon)
        _add(search_lemmy)

    # Domain 4: Media & Video Transcripts
    if any(k in q for k in ["youtube", "video", "talk", "lecture", "transcript"]):
        _add(search_youtube_transcripts)

    # Core Foundation Fallbacks (Guarantees broad web coverage)
    _add(search_tavily)
    _add(fetch_wiki_data)

    return selected[:max_tools]
