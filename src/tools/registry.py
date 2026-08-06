import os
import sys
import asyncio
import re
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import StructuredTool

async def _load_all_tools():
    servers = {
        "search": {"transport": "sse", "url": os.environ.get("MCP_SEARCH_SERVER_URL", "http://localhost:8001/sse")},
        "academic": {"transport": "sse", "url": os.environ.get("MCP_ACADEMIC_SERVER_URL", "http://localhost:8002/sse")},
        "dev": {"transport": "sse", "url": os.environ.get("MCP_DEV_SERVER_URL", "http://localhost:8003/sse")},
        "media_social": {"transport": "sse", "url": os.environ.get("MCP_MEDIA_SOCIAL_SERVER_URL", "http://localhost:8004/sse")},
        "extractor": {"transport": "sse", "url": os.environ.get("MCP_EXTRACTOR_SERVER_URL", "http://localhost:8005/sse")},
    }
    
    try:
        client = MultiServerMCPClient(servers)
        return await client.get_tools()
    except Exception as e:
        error_msg = (
            "\n" + "=" * 60 + "\n"
            "CRITICAL ERROR: Could not connect to AWIS MCP Servers.\n"
            f"Details: {e}\n"
            "Please ensure you have started the MCP servers by running:\n"
            "    python -m src.mcp_servers.run_all\n"
            + "=" * 60 + "\n"
        )
        raise RuntimeError(error_msg) from e

def _make_sync_tool(async_tool):
    """Wraps an async MCP tool into a synchronous LangChain StructuredTool."""
    def sync_caller(*args, **kwargs):
        return asyncio.run(async_tool.ainvoke(*args, **kwargs))
        
    return StructuredTool(
        name=async_tool.name,
        description=async_tool.description,
        args_schema=async_tool.args_schema,
        func=sync_caller,
        coroutine=async_tool.coroutine
    )

def get_all_tools():
    """Synchronous wrapper to resolve all MCP tools dynamically at startup."""
    raw_mcp_tools = asyncio.run(_load_all_tools())
    return [_make_sync_tool(t) for t in raw_mcp_tools]

# Load tools at module level
ALL_MCP_TOOLS = get_all_tools()

def _get_tool(name: str):
    for t in ALL_MCP_TOOLS:
        if t.name == name:
            return t
    return None

# 1. Subagent Scoped Toolsets
RESEARCHER_TOOLS = [t for t in [
    _get_tool("search_arxiv"),
    _get_tool("search_arxiv_papers"),
    _get_tool("search_clinical_trials"),
    _get_tool("fetch_wiki_data"),
    _get_tool("search_web_news"),
    _get_tool("search_tavily"),
    _get_tool("search_exa_semantic"),
    _get_tool("search_github_repos"),
    _get_tool("search_youtube_transcripts"),
    _get_tool("extract_pdf_with_pdfplumber"),
    _get_tool("extract_pdf"),
    _get_tool("extract_webpage"),
    _get_tool("extract_wikipedia_summary")
] if t is not None]

VERIFIER_TOOLS = [t for t in [
    _get_tool("fetch_wiki_data"),
    _get_tool("search_tavily"),
    _get_tool("search_stackexchange"),
    _get_tool("search_arxiv")
] if t is not None]

REPORTER_TOOLS = [t for t in [
    _get_tool("save_intelligence_report")
] if t is not None]

# 2. Master Registry containing all active tools across all modules
AWIS_TOOL_REGISTRY = [t for t in [
    _get_tool("search_arxiv"),
    _get_tool("search_arxiv_papers"),
    _get_tool("search_clinical_trials"),
    _get_tool("fetch_wiki_data"),
    _get_tool("search_web_news"),
    _get_tool("search_tavily"),
    _get_tool("search_exa_semantic"),
    _get_tool("find_working_searxng"),
    _get_tool("search_site_content"),
    _get_tool("find_site_feeds"),
    _get_tool("search_github_repos"),
    _get_tool("search_stackexchange"),
    _get_tool("search_youtube_transcripts"),
    _get_tool("search_youtube_transcripts_no_key"),
    _get_tool("search_mastodon"),
    _get_tool("search_lemmy"),
    _get_tool("extract_pdf_with_pdfplumber"),
    _get_tool("extract_pdf"),
    _get_tool("save_intelligence_report"),
    _get_tool("extract_webpage"),
    _get_tool("extract_wikipedia_summary"),
    _get_tool("monitor_rss_feed")
] if t is not None]

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
        if tool.name != "save_intelligence_report":
            tool_map[tool.name] = {"tool": tool, "score": 0}

    def _boost(tool_name: str, points: int):
        # Fallback map for MCP wrapper aliases
        if tool_name == "extract_pdf_with_pdfplumber":
            tool_name = "extract_pdf"
            
        if tool_name in tool_map:
            tool_map[tool_name]["score"] += points

    def _kw_match(keyword: str, text: str) -> bool:
        """Regex helper to enforce strict word boundary matching for keywords."""
        return re.search(rf"\b{re.escape(keyword)}\b", text) is not None

    # 1. Broad Real-Time Web & News (High priority for general, city, industry, market, or business queries)
    web_keywords = ["pune", "india", "city", "industry", "market", "job", "career", "development", "trend", "news", "company", "startup", "economy", "growth", "state"]
    if any(_kw_match(k, q) for k in web_keywords):
        _boost("search_tavily", 50)
        _boost("search_web_news", 40)

    # 2. Historical & Foundational Background (Wikipedia)
    wiki_keywords = ["history", "background", "overview", "what is", "definition", "pune", "city", "concept", "country"]
    if any(_kw_match(k, q) for k in wiki_keywords):
        _boost("fetch_wiki_data", 45)

    # 3. Software Engineering & Code Repositories
    code_keywords = ["code", "repo", "github", "python", "framework", "library", "sdk", "api", "architecture", "implementation", "open source"]
    if any(_kw_match(k, q) for k in code_keywords):
        _boost("search_github_repos", 45)
    if any(_kw_match(k, q) for k in ["stack", "overflow", "error", "bug", "how to", "issue", "exception"]):
        _boost("search_stackexchange", 45)

    # 4. Academic Research & arXiv Papers (Strictly triggered for explicit paper/math/study queries)
    academic_keywords = ["arxiv", "paper", "abstract", "peer-reviewed", "journal", "citation", "theorem", "proof", "benchmark dataset"]
    if any(_kw_match(k, q) for k in academic_keywords):
        _boost("search_arxiv", 60)
        _boost("search_arxiv_papers", 55)

    # Medical / Clinical
    if any(_kw_match(k, q) for k in ["clinical", "trial", "medical", "drug", "patient", "health", "disease", "pharma"]):
        _boost("search_clinical_trials", 60)

    # Community Sentiment
    if any(_kw_match(k, q) for k in ["mastodon", "lemmy", "community", "opinion", "sentiment", "discussion", "social"]):
        _boost("search_mastodon", 40)
        _boost("search_lemmy", 40)

    # YouTube Transcripts
    if any(_kw_match(k, q) for k in ["youtube", "video", "talk", "lecture", "transcript", "presentation"]):
        _boost("search_youtube_transcripts", 50)

    # Always ensure search_tavily and fetch_wiki_data have solid default scores for broad coverage
    _boost("search_tavily", 20)
    _boost("fetch_wiki_data", 15)

    # Sort tools by score descending
    sorted_items = sorted(tool_map.values(), key=lambda item: item["score"], reverse=True)
    
    # Return top max_tools unique tools
    return [item["tool"] for item in sorted_items[:max_tools]]