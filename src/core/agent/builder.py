import os

import deepagents.middleware.filesystem as fs_mw
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

from src.core.llm import build_production_llm
from src.core.agent.wrapper import SyncAgentWrapper
from src.tools.registry import (
    RESEARCHER_TOOLS,
    VERIFIER_TOOLS,
    REPORTER_TOOLS,
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
            },
            {
                "name": "Researcher",
                "description": "STEP 2 (ALWAYS CALL FIRST ON TURN 1): Scrapes live web search data via search_tavily, Wikipedia, and GitHub repos. MUST be executed before Reporter.",
                "system_prompt": (
                    "Execute assigned research tools (search_tavily, fetch_wiki_data) to gather facts, paper abstracts, paper URLs, arXiv IDs, and code repos. "
                    "Return a clean, factual summary containing all hard numbers, dates, paper links, and repo URLs."
                ),
                "tools": dynamic_research_tools,
            },
            {
                "name": "Verifier",
                "description": "STEP 3: Audits raw findings gathered by Researcher for credibility.",
                "system_prompt": (
                    "Audit research findings gathered by Researcher for credibility, source quality, and technical accuracy. "
                    "Use assigned search tools to cross-verify claims and return verified facts concisely."
                ),
                "tools": VERIFIER_TOOLS,
            },
            {
                "name": "Reporter",
                "description": "STEP 4 (STRICTLY FINAL STEP - NEVER CALL FIRST): Compiles final brief. CANNOT be called until Researcher finishes.",
                "system_prompt": (
                    "Compile a thorough, well-organized intelligence report using ONLY the research "
                    "findings provided in your task description. Do not introduce facts, links, "
                    "dates, repository names, or benchmark numbers that were not present in the "
                    "provided findings. "
                    "\n\n"
                    "Structure your report using whichever of the following sections are actually "
                    "supported by the findings — omit any section entirely if there is no relevant "
                    "material for it, rather than inventing content to fill it:\n"
                    "- Executive Summary & Core Insights\n"
                    "- Background & Context\n"
                    "- Technical Architecture & Workflows (only if the topic is a technical/software system)\n"
                    "- Code Repositories & Implementation Details (only if real repo links were found)\n"
                    "- Academic/Research Basis (only if real paper links were found)\n"
                    "- Community & Public Reception (if social/discussion data was found)\n"
                    "- Risks, Open Questions & Trade-offs\n"
                    "- Verified Source Citation Index (list only sources actually present in the findings)\n"
                    "\n"
                    "If the provided findings are sparse or the topic doesn't fit a technical "
                    "template, write a shorter, honest report rather than padding it with invented "
                    "detail. Call save_intelligence_report ONCE passing the complete report string "
                    "as report_content. Once save_intelligence_report finishes, output "
                    "'REPORT_SAVED_SUCCESSFULLY' and stop execution immediately."
                ),
                "tools": REPORTER_TOOLS,
            },
        ],
    )
    return SyncAgentWrapper(agent)