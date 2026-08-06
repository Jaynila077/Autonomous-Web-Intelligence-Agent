import os
import deepagents.middleware.filesystem as fs_mw
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from deepagents.middleware.filesystem import FilesystemPermission
from deepagents.middleware._tool_exclusion import _ToolExclusionMiddleware

from src.core.llm import build_production_llm
from src.core.agent.wrapper import SyncAgentWrapper
from src.tools.registry import (
    RESEARCHER_TOOLS,
    VERIFIER_TOOLS,
    REPORTER_TOOLS,
    select_dynamic_tools,
)

EXCLUDED_TOOLS = frozenset({"write_todos"})
tool_exclusion_mw = _ToolExclusionMiddleware(excluded=EXCLUDED_TOOLS)

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
    backend = FilesystemBackend(root_dir=vfs_path, virtual_mode=True)

    dynamic_research_tools = select_dynamic_tools(query, max_tools=4)

    deny_fs_permissions = [
    FilesystemPermission(operations=["read", "write"], paths=["/*", "/"], mode="deny")
    ]
   

    agent = create_deep_agent(
        model=llm,
        backend=backend,
        tools=[],
        permissions=deny_fs_permissions,
        middleware=[tool_exclusion_mw],
        system_prompt=(
            "Lead Orchestrator for AWIS. Your subagents are strictly: 'Planner', 'Researcher', 'Verifier', and 'Reporter'. "
            "1. Delegate to 'Researcher' on Turn 1 to execute search tools and gather live web facts. "
            "2. CRITICAL FOR VERIFIER: When delegating to 'Verifier' on Turn 2, you MUST copy ALL raw findings, web facts, numbers, dates, paper links, and repo links returned by Researcher into the description parameter. Verifier has NO access to Researcher's output except what you paste into this description — it cannot read files, search for Researcher's notes, or access any shared memory. If you do not paste the findings, Verifier has nothing to audit. "
            "3. CRITICAL FOR REPORTER: When delegating to 'Reporter', you MUST copy ALL raw findings, web facts, numbers, dates, paper links, and repo links from Researcher and Verifier into the description parameter so Reporter has complete factual context. Reporter also has NO access to any subagent's output except what you paste here."
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
                "middleware": [tool_exclusion_mw],
            },
            {
                "name": "Researcher",
                "description": "STEP 2 (ALWAYS CALL FIRST ON TURN 1): Scrapes live web search data via search_tavily, Wikipedia, and GitHub repos. MUST be executed before Reporter.",
                "system_prompt": (
                    "Execute assigned research tools (search_tavily, fetch_wiki_data, etc.) to gather facts, dates, numbers, and source links relevant to the query. "
                    "Use AT MOST 5-6 search calls total for the entire research task — broad, well-targeted queries, not one call per individual sub-fact. "
                    "Do not re-search the same fact with reworded queries — if a search already returned the information (e.g. a song's chart peak), use it and move on rather than searching again for confirmation. "
                    "Prioritize breadth over exhaustive per-item verification — a single good search covering 'top songs' as a whole is better than separate searches for each song's individual chart stats. "
                    "Return a clean, factual summary containing all hard numbers, dates, and source links you found."
                ),
                "tools": dynamic_research_tools,
                "middleware": [tool_exclusion_mw],
            },
            {
                "name": "Verifier",
                "description": "STEP 3: Audits raw findings gathered by Researcher for credibility.",
               "system_prompt": (
                    "Audit research findings gathered by Researcher for credibility, source quality, and technical accuracy. "
                    "The findings to audit are provided directly in your task description below — do not attempt to locate them via filesystem tools (ls, read_file, glob), as no such files exist. "
                    "Do NOT re-research every fact — the findings are provided directly, not something you need to rediscover. "
                    "Selectively execute AT MOST 2 search calls total, focused only on the single most load-bearing or riskiest claim (e.g. a statistic likely to be outdated, or a disputed/controversial fact). "
                    "Do not repeat an identical search query — if a search returns useful results, move on rather than re-issuing the same query. "
                    "Return a concise verification summary noting which facts are well-supported and which are uncertain."
                ),
                "tools": VERIFIER_TOOLS,
                "middleware": [tool_exclusion_mw],
            },
            {
                "name": "Reporter",
                "description": "STEP 4 (STRICTLY FINAL STEP - NEVER CALL FIRST): Compiles final brief directly as Markdown text. CANNOT be called until Researcher finishes.",
                "system_prompt": (
                    "You are the Lead Intelligence Reporter. You have NO tools available — you MUST NOT call 'write_file', 'read_file', 'list_dir', 'save_intelligence_report', or any function/tool of any kind. "
                    "Do NOT output XML function calls (<function=...>). "
                    "Your ONLY task is to write out a complete, well-structured research report directly as clean Markdown text in your final response, using ONLY the raw findings and verification notes provided in your task description. "
                    "\n\n"
                    "CRITICAL — CHOOSE SECTIONS BASED ON THE ACTUAL QUERY AND FINDINGS, NOT A FIXED TEMPLATE: "
                    "Do not force technical/academic sections (e.g. 'System Architecture', 'GitHub Repositories', 'arXiv Benchmark Audit') onto a query that has nothing to do with software, research papers, or engineering. "
                    "Instead, derive section headers from what the findings actually contain — for example, a person or public figure might warrant Biography, Career, Achievements, Controversies, Current Status; a technical topic might warrant Architecture, Implementation Patterns, Benchmarks, Trade-offs; a current-events topic might warrant Background, Key Developments, Different Perspectives, Outlook. "
                    "\n\n"
                    "Structure requirements: "
                    "- Use clear Markdown headers (##) for each section, tailored to the topic. "
                    "- Include a brief Executive Summary at the top. "
                    "- Include a Source Citation section at the end listing the sources referenced in the findings. "
                    "- Cite concrete facts, numbers, dates, and links exactly as given in the findings — never invent details not present in your task description. "
                    "- Write complete, multi-paragraph prose for every section — no placeholder text like 'content goes here'. "
                    "- Note explicitly (per the verification summary, if provided) which claims are well-supported versus disputed or unverified. "
                    "\n\n"
                    "Once you have written the full report as plain Markdown text, stop — do not call any tool, do not add any closing tool-call syntax."
                ),
                "tools": [],
                "middleware": [tool_exclusion_mw],
            },
        ],
    )
    return SyncAgentWrapper(agent), vfs_path