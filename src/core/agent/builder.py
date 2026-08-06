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


def build_awis_agent(
    query: str = "Agentic AI Architectures",
    user_id: str = "default",
    job_id: str = "default",
):
    # Job-scoped workspace: prevents concurrent jobs from racing on the same
    # shared filesystem path when multiple users' jobs run at the same time
    # via the arq worker queue.
    vfs_path = os.path.abspath(f"./workspace/users/{user_id}/jobs/{job_id}")
    reports_path = os.path.join(vfs_path, "reports")
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
                    "Audit research findings gathered by Researcher for credibility, source quality, and technical accuracy. "
                    "Use assigned search tools to cross-verify claims and return verified facts concisely."
                ),
                "tools": VERIFIER_TOOLS,
                "middleware": [],
            },
            {
                "name": "Reporter",
                "description": "STEP 4 (STRICTLY FINAL STEP - NEVER CALL FIRST): Compiles final brief. CANNOT be called until Researcher finishes.",
                "system_prompt": (
                    "Compile an exhaustive, highly detailed, production-grade intelligence report (minimum 1,500 words) using the research findings provided in your task description. "
                    "You MUST include hard facts, dates, paper titles, arXiv links, GitHub repository links, concrete architecture explanations, and verified benchmarks. "
                    "Structure between 9-15 clear sections: "
                    "1. Executive Summary & Core Insights, "
                    "2. Deep Technical System Architecture & Workflows, "
                    "3. Production Code Patterns & GitHub Repositories (with links), "
                    "4. Empirical Benchmark & Paper Abstract Audit (with arXiv links), "
                    "5. Risk, Bottlenecks & Production Trade-offs, "
                    "6. Verified Source Citation Index. "
                    "NEVER use dummy placeholder text like 'content goes here'. Write complete, thorough, comprehensive paragraphs for every section. "
                    "Call save_intelligence_report ONCE passing the complete 6-section report string as report_content. "
                    "CRITICAL: Once save_intelligence_report finishes, output 'REPORT_SAVED_SUCCESSFULLY' and stop execution immediately."
                ),
                "tools": REPORTER_TOOLS,
                "middleware": [],
            },
        ],
    )
    return SyncAgentWrapper(agent), vfs_path