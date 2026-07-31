from src.tools.academic_tools import search_arxiv, search_clinical_trials
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
from src.tools.media_tools import search_youtube
from src.tools.social_tools import (
    search_mastodon,
    search_lemmy,
)
from src.tools.extractor_tools import (
    extract_pdf_with_pdfplumber,
    extract_github_readme,
    extract_youtube_transcript,
    extract_lemmy_post,
    save_intelligence_report,
)

# Subagent Scoped Toolsets (keeps prompt tokens light & prevents 429 rate limits)
RESEARCHER_TOOLS = [
    search_arxiv,
    search_clinical_trials,
    fetch_wiki_data,
    search_web_news,
    search_tavily,
    search_exa_semantic,
    search_github_repos,
    extract_github_readme,
    search_youtube,
    extract_youtube_transcript,
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

# Master Registry containing every tool the app knows about
AWIS_TOOL_REGISTRY = [
    # -- Academic / research --
    search_arxiv,
    search_clinical_trials,

    # -- General web --
    fetch_wiki_data,
    search_web_news,
    search_tavily,
    search_exa_semantic,
    find_working_searxng,
    search_site_content,
    find_site_feeds,

    # -- Dev / code --
    search_github_repos,
    search_stackexchange,

    # -- Media --
    search_youtube,

    # -- Social --
    search_mastodon,
    search_lemmy,

    # -- Extractors: expensive, targeted full-content fetch (call after a search tool) --
    extract_pdf_with_pdfplumber,
    extract_github_readme,
    extract_youtube_transcript,
    extract_lemmy_post,

    # -- Output --
    save_intelligence_report,
]


def select_dynamic_tools(query: str, max_tools: int = 2) -> list:
    """
    Dynamic Tool Router: Inspects the user's research query and selects
    the top N most relevant tools from AWIS_TOOL_REGISTRY.
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
    if any(k in q for k in ["clinical", "trial", "medical", "drug", "patient", "health", "disease"]):
        _add(search_clinical_trials)

    # Domain 2: Code & Engineering
    if any(k in q for k in ["code", "repo", "github", "python", "framework", "library", "sdk"]):
        _add(search_github_repos)
    if any(k in q for k in ["stack", "overflow", "error", "bug", "how to", "issue"]):
        _add(search_stackexchange)

    # Domain 3: Community & Social Sentiment
    if any(k in q for k in ["mastodon", "fediverse", "social"]):
        _add(search_mastodon)
    if any(k in q for k in ["lemmy"]):
        _add(search_lemmy)

    # Domain 4: Media & Video
    if any(k in q for k in ["youtube", "video", "talk", "lecture", "transcript"]):
        _add(search_youtube)

    # Core Foundation Fallbacks (Guarantees broad web coverage)
    _add(search_tavily)
    _add(fetch_wiki_data)

    return selected[:max_tools]