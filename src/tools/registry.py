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
from src.tools.media_tools import search_youtube_transcripts, search_youtube_transcripts_no_key
from src.tools.social_tools import (
    search_reddit,
    search_bluesky,
    search_mastodon,
    search_lemmy,
    search_tumblr,
    search_vk,
)
from src.tools.extractor_tools import extract_pdf_with_pdfplumber, save_intelligence_report

# Subagent Scoped Toolsets (keeps prompt tokens light & prevents 429 rate limits)
RESEARCHER_TOOLS = [
    search_arxiv,
    search_clinical_trials,
    fetch_wiki_data,
    search_web_news,
    search_tavily,
    search_exa_semantic,
    search_github_repos,
    search_youtube_transcripts,
    search_reddit,
    search_bluesky,
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

# Master Registry containing all 18+ tools
AWIS_TOOL_REGISTRY = [
    search_arxiv,
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
    search_reddit,
    search_bluesky,
    search_mastodon,
    search_lemmy,
    search_tumblr,
    search_vk,
    extract_pdf_with_pdfplumber,
    save_intelligence_report,
]

def select_dynamic_tools(query: str, max_tools: int = 2) -> list:
    """
    Dynamic Tool Router: Inspects the user's research query and selects 
    the top 2 most relevant tools from all 18+ tools in AWIS_TOOL_REGISTRY.
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
    if any(k in q for k in ["reddit", "opinion", "review", "discussion", "community"]):
        _add(search_reddit)
    if any(k in q for k in ["bluesky", "mastodon", "fediverse", "social"]):
        _add(search_bluesky)
        _add(search_mastodon)

    # Domain 4: Media & Video Transcripts
    if any(k in q for k in ["youtube", "video", "talk", "lecture", "transcript"]):
        _add(search_youtube_transcripts)

    # Core Foundation Fallbacks (Guarantees broad web coverage)
    _add(search_tavily)
    _add(fetch_wiki_data)

    return selected[:max_tools]
