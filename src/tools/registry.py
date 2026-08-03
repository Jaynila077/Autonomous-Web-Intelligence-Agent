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


def select_dynamic_tools(query: str, max_tools: int = 4) -> list:
    """
    Intelligent Semantic Tool Router: Evaluates query intent against tool capability profiles
    and dynamically selects up to max_tools (default: 4) optimal tools.
    Eliminates schema noise while preserving multi-source research capabilities.
    """
    q = query.lower()
    tool_map = {}

    # Initialize all tools with base priority score
    for tool in AWIS_TOOL_REGISTRY:
        if tool != save_intelligence_report:
            tool_map[tool.name] = {"tool": tool, "score": 0}

    def _boost(tool_name: str, points: int):
        if tool_name in tool_map:
            tool_map[tool_name]["score"] += points

    # 1. Broad Real-Time Web & News (High priority for general, city, industry, market, or business queries)
    web_keywords = ["pune", "india", "city", "industry", "market", "job", "career", "development", "trend", "news", "company", "startup", "economy", "growth", "state"]
    if any(k in q for k in web_keywords):
        _boost("search_tavily", 50)
        _boost("search_web_news", 40)

    # 2. Historical & Foundational Background (Wikipedia)
    wiki_keywords = ["history", "background", "overview", "what is", "definition", "pune", "city", "concept", "country"]
    if any(k in q for k in wiki_keywords):
        _boost("fetch_wiki_data", 45)

    # 3. Software Engineering & Code Repositories
    code_keywords = ["code", "repo", "github", "python", "framework", "library", "sdk", "api", "architecture", "implementation", "open source"]
    if any(k in q for k in code_keywords):
        _boost("search_github_repos", 45)
    if any(k in q for k in ["stack", "overflow", "error", "bug", "how to", "issue", "exception"]):
        _boost("search_stackexchange", 45)

    # 4. Academic Research & arXiv Papers (Strictly triggered for explicit paper/math/study queries)
    academic_keywords = ["arxiv", "paper", "abstract", "peer-reviewed", "journal", "citation", "theorem", "proof", "benchmark dataset"]
    if any(k in q for k in academic_keywords):
        _boost("search_arxiv", 60)
        _boost("search_arxiv_papers", 55)

    # Medical / Clinical
    if any(k in q for k in ["clinical", "trial", "medical", "drug", "patient", "health", "disease", "pharma"]):
        _boost("search_clinical_trials", 60)

    # Community Sentiment
    if any(k in q for k in ["mastodon", "lemmy", "community", "opinion", "sentiment", "discussion", "social"]):
        _boost("search_mastodon", 40)
        _boost("search_lemmy", 40)

    # YouTube Transcripts
    if any(k in q for k in ["youtube", "video", "talk", "lecture", "transcript", "presentation"]):
        _boost("search_youtube_transcripts", 50)

    # Always ensure search_tavily and fetch_wiki_data have solid default scores for broad coverage
    _boost("search_tavily", 20)
    _boost("fetch_wiki_data", 15)

    # Sort tools by score descending
    sorted_items = sorted(tool_map.values(), key=lambda item: item["score"], reverse=True)

    # Return top max_tools unique tools
    return [item["tool"] for item in sorted_items[:max_tools]]
