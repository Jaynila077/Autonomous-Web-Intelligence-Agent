from src.tools.academic_tools import search_arxiv_papers
from src.tools.blog_tools import search_domain_with_dork, search_with_exa
from src.tools.dev_tools import search_github_repos, search_stackexchange
from src.tools.extractor_tools import (
    extract_pdf_with_pdfplumber, 
    extract_article_text,
    extract_youtube_transcript,
    extract_github_readme,
    extract_lemmy_post
)
from src.tools.health_tools import search_clinical_trials
from src.tools.news_tools import search_news_duckduckgo, monitor_rss_feed
from src.tools.reporting_tools import save_intelligence_report
from src.tools.search_tools import (
    search_arxiv, 
    find_working_searx_instances, 
    tavily_basic_search, 
    tavily_advanced_research, 
    extract_webpage_with_tavily
)
from src.tools.social_tools import search_mastodon, search_lemmy
from src.tools.web_tools import search_site_content, find_site_feeds
from src.tools.wiki_tools import extract_wikipedia_summary
from src.tools.youtube_tools import search_youtube_videos

# ==========================================
# SUBAGENT SCOPED TOOLSETS (Context Window Optimization)
# ==========================================

# 1. SCOUT / RESEARCHER (Dev 2): Only needs tools that actively discover URLs and initial claims.
RESEARCHER_TOOLS = [
    search_arxiv,
    search_clinical_trials,
    search_with_exa,
    search_domain_with_dork,
    search_news_duckduckgo,
    monitor_rss_feed,
    tavily_basic_search,
    tavily_advanced_research,
    search_youtube_videos,
    search_site_content,
    find_site_feeds,
    search_github_repos,
    search_stackexchange,
    search_mastodon,
    search_lemmy,
]

# 2. EXTRACTOR ENGINE (Dev 3): Only needs tools that parse and clean targeted documents into Markdown.
EXTRACTOR_TOOLS = [
    extract_pdf_with_pdfplumber,
    extract_article_text,
    extract_webpage_with_tavily,
    extract_youtube_transcript,
    extract_github_readme,
    extract_lemmy_post
]

# 3. VERIFIER (Dev 4): Strictly authoritative databases for fact-checking to drop hallucinations.
VERIFIER_TOOLS = [
    extract_wikipedia_summary,
    search_clinical_trials,
    search_arxiv_papers,
    tavily_advanced_research, # Authoritative if include_domains is used
    search_stackexchange 
]

# 4. REPORTER (Dev 5): Synthesizing and saving the final intelligence brief.
REPORTER_TOOLS = [
    save_intelligence_report
]

# 5. INFRASTRUCTURE: Decentralized routing checks (likely executed by system, not LLM directly)
INFRA_TOOLS = [
    find_working_searx_instances,
]

# Master Registry containing all tools
AWIS_TOOL_REGISTRY = list(set(
    RESEARCHER_TOOLS + EXTRACTOR_TOOLS + VERIFIER_TOOLS + REPORTER_TOOLS + INFRA_TOOLS
))

# ==========================================
# DYNAMIC TOOL ROUTER
# ==========================================

def select_dynamic_tools(query: str, max_tools: int = 4) -> list:
    """
    Dynamic Tool Router: Inspects the user's research query and selects 
    the top most relevant tools from the AWIS registry to prevent token bloat.
    """
    q = query.lower()
    selected = []

    def _add(tool):
        if tool not in selected:
            selected.append(tool)

    # Domain 1: Academic, Scientific & Public Health
    if any(k in q for k in ["paper", "arxiv", "research", "study", "model", "algorithm"]):
        _add(search_arxiv)
    if any(k in q for k in ["clinical", "trial", "medical", "drug", "health", "vaccine", "who"]):
        _add(search_clinical_trials)

    # Domain 2: Deep Web, Blogs & Technical Documentation
    if any(k in q for k in ["blog", "tutorial", "guide", "documentation", "how to", "scrapfly"]):
        _add(search_domain_with_dork)
        _add(search_with_exa) # Exa is incredible for semantic tech/blog searches

    # Domain 3: Breaking News & Feeds
    if any(k in q for k in ["news", "latest", "announcement", "release", "today"]):
        _add(search_news_duckduckgo)
        _add(monitor_rss_feed)

    # Domain 4: Media & Video
    if any(k in q for k in ["youtube", "video", "talk", "lecture", "watch", "channel"]):
        _add(search_youtube_videos)
        _add(extract_youtube_transcript)

    # Domain 5: Deep File Extraction triggers
    if any(k in q for k in ["pdf", "document", "file", "download"]):
        _add(extract_pdf_with_pdfplumber)

    # Domain 6: Code & Engineering
    if any(k in q for k in ["code", "repo", "github", "python", "framework", "library", "sdk"]):
        _add(search_github_repos)
    if any(k in q for k in ["stack", "overflow", "error", "bug", "issue"]):
        _add(search_stackexchange)

    # Domain 7: Community & Social Sentiment
    if any(k in q for k in ["mastodon", "fediverse", "social"]):
        _add(search_mastodon)
    if any(k in q for k in ["lemmy"]):
        _add(search_lemmy)

    # Core Foundation Fallbacks (Always include general robust options)
    _add(tavily_advanced_research)
    _add(extract_wikipedia_summary)

    return selected[:max_tools]  