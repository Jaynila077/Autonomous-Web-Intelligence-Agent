import os

import deepagents.middleware.filesystem as fs_mw
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

from src.core.llm import build_production_llm
from src.core.agent.wrapper import SyncAgentWrapper
from src.tools.registry import (
    VERIFIER_TOOLS,
    select_dynamic_tools,
)

# Lightweight VFS System Prompt: Deletes 6,400 tokens of Linux shell manuals
# while preserving 100% of VFS file saving USP (workspace/raw, workspace/reports)
fs_mw.FILESYSTEM_SYSTEM_PROMPT = "Workspace VFS Active: Use write_file to save notes, read_file to read notes, and list_dir to view workspace."


def build_awis_agent(query: str = "Agentic AI Architectures"):
    vfs_path = os.path.abspath("./workspace")
    reports_path = os.path.abspath("./workspace/reports")
    os.makedirs(vfs_path, exist_ok=True)
    os.makedirs(reports_path, exist_ok=True)

    llm = build_production_llm()
    backend = FilesystemBackend(root_dir=vfs_path, virtual_mode=False)

    dynamic_research_tools = select_dynamic_tools(query, max_tools=4)

    agent = create_deep_agent(
        model=llm,
        backend=backend,
        tools=[],
        system_prompt=(
            "Lead Orchestrator for AWIS. Your subagents are strictly: 'Planner', 'Researcher', 'Verifier', and 'Reporter'. "
            "1. Delegate to 'Researcher' on Turn 1 to execute search tools and gather live web facts. "
            "2. Delegate to 'Verifier' on Turn 2 to audit findings for credibility. "
            "3. CRITICAL FOR REPORTER: When delegating to 'Reporter', you MUST copy ALL raw findings, web facts, numbers, dates, paper links, and repo links from Researcher and Verifier into the description parameter so Reporter has complete factual context."
        ),
        subagents=[
            {
                "name": "Planner",
                "description": "STEP 1: Creates structured multi-domain research plan.",
                "system_prompt": (
                    "Create a concise 4-step research plan covering: "
                    "Academic, Web/Wiki, Developer code, and Community opinion. Be direct and concise."
                ),
                "tools": [],
                "middleware": [],
            },
            {
                "name": "Researcher",
                "description": "STEP 2 (ALWAYS CALL FIRST ON TURN 1): Scrapes live web search data via search_tavily, Wikipedia, and GitHub repos. MUST be executed before Reporter.",
                "system_prompt": (
                    "Execute assigned research tools (search_tavily, fetch_wiki_data) to gather facts, paper abstracts, paper URLs, arXiv IDs, and code repos. "
                    "Return a clean, factual summary containing all hard numbers, dates, paper links, and repo URLs."
                ),
                "tools": dynamic_research_tools,
                "middleware": [],
            },
            {
                "name": "Verifier",
                "description": "STEP 3: Audits raw findings gathered by Researcher for credibility.",
                "system_prompt": (
                    "EFFICIENT VERIFICATION MANDATE: You do NOT need to verify data for every tool used in the research phase. "
                    "Selectively execute 1 to 2 primary tools (e.g., fetch_wiki_data or search_tavily) to quickly verify core claims, dates, and numbers, then summarize credibility concisely."
                ),
                "tools": VERIFIER_TOOLS,
                "middleware": [],
            },
            {
                "name": "Reporter",
                "description": "STEP 4 (STRICTLY FINAL STEP): Compiles final brief directly as Markdown text without calling any VFS file tools.",
                "system_prompt": (
                    "You are the Lead Intelligence Reporter. You MUST NOT call 'write_file', 'read_file', 'list_dir', 'save_intelligence_report', or any function tools. "
                    "Do NOT output XML function calls (<function=...>). "
                    "Your ONLY task is to write out the full, exhaustive 6-section research report (minimum 1,500 words) directly as clean Markdown text in your final response:\n\n"
                    "1. Executive Summary & Core Insights\n"
                    "2. Deep Technical System Architecture & Workflows\n"
                    "3. Production Code Patterns & GitHub Repositories (with links)\n"
                    "4. Empirical Benchmark & Paper Abstract Audit (with arXiv links)\n"
                    "5. Risk, Bottlenecks & Production Trade-offs\n"
                    "6. Verified Source Citation Index\n\n"
                    "Write complete, multi-paragraph text for every single section."
                ),
                "tools": [],
                "middleware": [],
            },
        ],
    )
    return SyncAgentWrapper(agent)