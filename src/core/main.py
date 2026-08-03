import sys
import os
import re
import json
import requests
from datetime import datetime
import time
import asyncio
from dotenv import load_dotenv

load_dotenv(override=True)

import deepagents.middleware.filesystem as fs_mw

# Lightweight VFS System Prompt: Deletes 6,400 tokens of Linux shell manuals
# while preserving 100% of VFS file saving USP (workspace/raw, workspace/reports)
fs_mw.FILESYSTEM_SYSTEM_PROMPT = "Workspace VFS Active: Use write_file to save notes, read_file to read notes, and list_dir to view workspace."

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import trim_messages, AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from src.tools.registry import (
    RESEARCHER_TOOLS,
    VERIFIER_TOOLS,
    REPORTER_TOOLS,
    select_dynamic_tools,
)
from src.tools.cache_manager import cache_manager

# 1. Message Trimmer for context token capping (~4 chars per token)
message_trimmer = trim_messages(
    max_tokens=60000,
    strategy="last",
    token_counter="approximate",
    include_system=True,
    start_on=None,
)

class TokenLoggerCallback(BaseCallbackHandler):
    """
    Real-time token usage and live tool execution logger callback (Windows CP1252 safe).
    """
    def on_tool_start(self, serialized, input_str, **kwargs):
        name = serialized.get("name") if isinstance(serialized, dict) else str(serialized)
        try:
            print(f"\n[LIVE TOOL EXECUTION] Executing Tool: '{name}'", flush=True)
            print(f"     Parameters : {input_str}\n", flush=True)
        except Exception:
            pass

    def on_llm_end(self, response, **kwargs):
        for generations in response.generations:
            for gen in generations:
                info = getattr(gen, "generation_info", {}) or {}
                token_usage = info.get("token_usage") or info.get("usage")
                if token_usage:
                    prompt_tok = token_usage.get("prompt_tokens") or token_usage.get("prompt_eval_count") or "N/A"
                    compl_tok = token_usage.get("completion_tokens") or token_usage.get("eval_count") or "N/A"
                    total_tok = token_usage.get("total_tokens") or "N/A"
                    try:
                        print(f"\n[LLM Token Usage Report]", flush=True)
                        print(f"     Prompt Tokens     : {prompt_tok}", flush=True)
                        print(f"     Completion Tokens : {compl_tok}", flush=True)
                        print(f"     Total Tokens      : {total_tok}", flush=True)
                        print(f"     Cost              : $0.00 (100% FREE)\n", flush=True)
                    except Exception:
                        pass

def _validate_groq_model(model_name: str, api_key: str) -> None:
    try:
        resp = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        resp.raise_for_status()
        live_ids = {m["id"] for m in resp.json().get("data", [])}
    except Exception:
        return
    if model_name not in live_ids:
        print(
            f"\nWARNING: '{model_name}' is not in Groq's current live model list.\n"
            f"Currently available models include:\n"
            f"  {sorted(live_ids)}\n"
            f"Set GROQ_MODEL in .env to one of the above.\n"
        )

class ToolParsingChatGroq(ChatGroq):
    """
    Parses raw function XML text (<function=name(...)}></function>) from Llama models on Groq.
    Catches Groq HTTP 400 failed_generation exceptions and converts them into valid tool calls.
    """
    def _generate(self, messages, **kwargs):
        trimmed_messages = message_trimmer.invoke(messages)
        res = None
        text = ""
        try:
            res = super()._generate(trimmed_messages, **kwargs)
        except Exception as e:
            err_str = str(e)
            if hasattr(e, "body") and isinstance(e.body, dict):
                text = e.body.get("failed_generation", "")
            if not text and "failed_generation" in err_str:
                match_txt = re.search(r"failed_generation'?: '(.*?)'\}", err_str, re.DOTALL)
                if match_txt:
                    text = match_txt.group(1)

            if text and "<function=" in text:
                name_match = re.search(r'<function=([a-zA-Z0-9_]+)', text)
                json_match = re.search(r'(\{.*\})', text, re.DOTALL)
                if name_match:
                    tool_name = name_match.group(1)
                    args = {}
                    if json_match:
                        raw_json = json_match.group(1).split("</function>")[0].strip()
                        try:
                            args = json.loads(raw_json)
                        except Exception:
                            args = {}

                    ai_msg = AIMessage(
                        content="",
                        tool_calls=[{
                            "name": tool_name,
                            "args": args,
                            "id": f"call_{int(time.time()*1000)}",
                            "type": "tool_call"
                        }]
                    )
                    gen = ChatGeneration(message=ai_msg)
                    return ChatResult(generations=[gen])
            raise e

        for generations in res.generations:
            for gen in generations:
                msg = getattr(gen, "message", None)
                if msg and hasattr(msg, "content") and isinstance(msg.content, str):
                    text_content = msg.content
                    if "<function=" in text_content:
                        name_match = re.search(r'<function=([a-zA-Z0-9_]+)', text_content)
                        if name_match:
                            tool_name = name_match.group(1)
                            json_match = re.search(r'(\{.*\})', text_content, re.DOTALL)
                            args = {}
                            if json_match:
                                raw_json = json_match.group(1).split("</function>")[0].strip()
                                try:
                                    args = json.loads(raw_json)
                                except Exception:
                                    args = {}
                            msg.tool_calls = [{
                                "name": tool_name,
                                "args": args,
                                "id": f"call_{int(time.time()*1000)}",
                                "type": "tool_call"
                            }]
                            msg.content = ""
        return res

def build_production_llm():
    token_logger = TokenLoggerCallback()

    # 1. Primary Option: NVIDIA NIM API (meta/llama-3.1-70b-instruct)
    nvidia_key = os.getenv("NVIDIA_API_KEY")
    if nvidia_key:
        return ChatOpenAI(
            model=os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct"),
            openai_api_key=nvidia_key,
            openai_api_base="https://integrate.api.nvidia.com/v1",
            temperature=0.0,
            max_retries=5,
            parallel_tool_calls=False,
            callbacks=[token_logger]
        )

    # 2. Secondary Option: Groq LPU
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        _validate_groq_model(model_name, groq_key)
        return ToolParsingChatGroq(
            model_name=model_name,
            groq_api_key=groq_key,
            temperature=0.0,
            max_retries=5,
            parallel_tool_calls=False,
            callbacks=[token_logger]
        )

    gh_token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if gh_token:
        return ChatOpenAI(
            model=os.getenv("GITHUB_MODEL", "gpt-4o-mini"),
            openai_api_key=gh_token,
            openai_api_base="https://models.inference.ai.azure.com",
            temperature=0.0,
            max_retries=5,
            parallel_tool_calls=False,
            callbacks=[token_logger]
        )

    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
                google_api_key=gemini_key,
                temperature=0.0,
                max_retries=5,
                callbacks=[token_logger]
            )
        except ImportError:
            pass

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        return ChatOpenAI(
            model=os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-72b-instruct"),
            openai_api_key=openrouter_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.0,
            max_retries=5,
            parallel_tool_calls=False,
            callbacks=[token_logger]
        )

    raise ValueError("No valid API key found in environment variables.")


class SyncAgentWrapper:
    """
    Bridges async MCP tools for synchronous callers by wrapping the compiled agent.
    Intercepts .invoke() and safely routes it to .ainvoke() within an event loop.
    """
    def __init__(self, agent):
        self.agent = agent

    def invoke(self, *args, **kwargs):
        return asyncio.run(self.agent.ainvoke(*args, **kwargs))

    def __getattr__(self, name):
        return getattr(self.agent, name)


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
            },
        ],
    )
    
    return SyncAgentWrapper(agent)

def run_pipeline(raw_query: str) -> str:
    clean_query = re.sub(r'\s+', ' ', raw_query).strip()
    if not clean_query:
        return "Error: Empty query provided."

    stats = cache_manager.get_stats()

    print("=" * 60)
    print("       AWIS Production Web Intelligence Pipeline            ")
    print("=" * 60)
    print(f"Target Query : '{clean_query}'")
    print(f"Cache Volume : {stats['total_entries']} entries ({stats['size_bytes'] / 1024:.1f} KB)")
    print()

    agent = build_awis_agent(clean_query)

    def _looks_like_leaked_tool_call(text: str) -> bool:
        stripped = text.strip()
        if "# Executive Summary" in stripped or "# Technical Analysis" in stripped or "# Intelligence Report" in stripped:
            return False
        return (stripped.startswith('{"type": "function"') or stripped.startswith("{'type': 'function'")) and not stripped.endswith("}")

    latest_file = os.path.abspath("./workspace/latest_report.md")
    if os.path.exists(latest_file):
        try:
            os.remove(latest_file)
        except Exception:
            pass

    max_attempts = 3
    final_output = None
    last_error = None

    token_logger = TokenLoggerCallback()

    for attempt in range(1, max_attempts + 1):
        try:
            response = agent.invoke(
                {"messages": [{"role": "user", "content": clean_query}]},
                config={"recursion_limit": 50, "callbacks": [token_logger]},
            )
        except Exception as e:
            last_error = e
            if "tool_use_failed" in str(e) and attempt < max_attempts:
                print(f"\nTool-call formatting glitch (attempt {attempt}/{max_attempts}) -- retrying...")
                continue
            print(f"\nPipeline failed during execution.\nFULL ERROR: {e}\n")
            return f"Error: Pipeline execution failed -- {e}"

        if os.path.exists(latest_file):
            with open(latest_file, "r", encoding="utf-8") as f:
                candidate_output = f.read()
        else:
            last_message = response["messages"][-1]
            candidate_output = last_message.content if isinstance(last_message.content, str) else str(last_message.content)

        if _looks_like_leaked_tool_call(candidate_output):
            last_error = "Model leaked a tool call as plain text instead of executing it."
            if attempt < max_attempts:
                print(f"\nLeaked tool-call detected in output (attempt {attempt}/{max_attempts}) -- retrying...")
                continue
            print(f"\nPipeline failed: model repeatedly leaked tool calls instead of executing them.\n")
            return f"Error: {last_error}"

        final_output = candidate_output
        print("\nPipeline Execution Finished Successfully!")
        break

    if final_output is None:
        return f"Error: Pipeline execution failed after {max_attempts} attempts -- {last_error}"

    print("\n" + "=" * 60)
    print("                FINAL INTELLIGENCE REPORT                ")
    print("=" * 60 + "\n")
    print(final_output)
    print("\n" + "=" * 60)
    print(f"Latest Report : {latest_file}\n")
    return final_output

if __name__ == "__main__":
    query_arg = sys.argv[1] if len(sys.argv) > 1 else "Latest advances in Agentic AI architectures"
    run_pipeline(query_arg)