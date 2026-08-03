import sys
import os
import re
import json
import requests
from datetime import datetime
import time
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
from langchain_core.messages import trim_messages, AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from src.tools.registry import (
    RESEARCHER_TOOLS,
    VERIFIER_TOOLS,
    REPORTER_TOOLS,
    AWIS_TOOL_REGISTRY,
    select_dynamic_tools,
)
from src.tools.cache_manager import cache_manager


# 1. Message Trimmer for context token capping (~4 chars per token)
#
# start_on='human' is required, not optional. With strategy="last", trim_messages
# keeps a contiguous tail of the message list. Without start_on, the cut point can
# land between an AIMessage(tool_calls=[...]) and its corresponding ToolMessage,
# leaving the ToolMessage as the first message of the surviving slice -- which
# OpenAI-compatible APIs reject with:
#   "messages with role 'tool' must be a response to a preceeding message with
#    'tool_calls'"
# start_on='human' forces trimming to keep walking backward until the first
# surviving message (after the preserved system message) is a HumanMessage,
# which structurally guarantees no orphaned ToolMessage can lead the kept slice.
# Verified against the installed langchain-core (1.5.3): there is no automatic
# orphan-ToolMessage stripping built into trim_messages itself at this version,
# so start_on is the actual fix, not a belt-and-suspenders addition.
#
# max_tokens=20000 (was 2500): 2500 was calibrated for Groq's original small
# fallback path but is far too tight for gpt-5-nano, whose write_todos/task
# responses routinely run 4,000-6,000+ tokens EACH. At 2500 tokens, the
# orchestrator's own record of "Step 1 (Planner) already completed" gets
# evicted almost every turn, so it has no memory of its own progress and
# re-delegates to Planner repeatedly instead of advancing -- confirmed live:
# 'task'->Planner fired again at calls #1, #5, #8, #12 in a single run,
# never reaching Researcher. 20000 gives enough headroom for several turns
# of orchestrator state to survive trimming, and is still comfortably within
# every fallback provider's context window (NVIDIA/Groq/Gemini/OpenRouter all
# support well over 20K tokens). This is independent of deepagents' own
# built-in SummarizationMiddleware, which is wired in separately and triggers
# at 85% of the model's real context window (~231K tokens for gpt-5-nano's
# 272K profile) -- confirmed via model.profile that it never engaged in the
# runs that exhibited this loop, since total usage peaked around 80K tokens.
message_trimmer = trim_messages(
    max_tokens=20000,
    strategy="last",
    token_counter="approximate",
    include_system=True,
    start_on="human",
)


def _strip_orphaned_tool_messages(messages: list) -> list:
    """
    Safety-net filter, run AFTER message_trimmer.

    start_on='human' should already make orphaned ToolMessages impossible, but
    this is a cheap, defensive second layer: it drops any ToolMessage whose
    tool_call_id has no matching tool_calls entry among the AIMessages present
    in the same (already-trimmed) list. This protects against edge cases (e.g.
    a future langchain-core version changing start_on semantics, or a message
    list that reaches the trimmer already malformed) without changing behavior
    in the normal case.
    """
    valid_call_ids = {
        tc.get("id")
        for m in messages
        if isinstance(m, AIMessage)
        for tc in (m.tool_calls or [])
        if tc.get("id")
    }
    return [
        m for m in messages
        if not (isinstance(m, ToolMessage) and m.tool_call_id not in valid_call_ids)
    ]


class TokenLoggerCallback(BaseCallbackHandler):
    """
    Per-LLM-call analysis logger.

    For EVERY LLM call anywhere in the pipeline (orchestrator + all 4 subagents),
    this prints and persists:
      - a running call number
      - which model/provider handled it
      - a snippet of the input that triggered this specific call
      - which tools (if any) this call's response requested
      - tokens used by this call, AND the running cumulative total for the whole run

    Token usage is NOT reliably found on `generation_info` across providers.
    In practice it shows up in one of three places depending on provider/SDK version:
      1. response.llm_output["token_usage"] / ["usage"]   (OpenAI-compatible: NVIDIA NIM, Groq, GitHub Models, OpenRouter)
      2. message.usage_metadata                            (LangChain's standardized field, e.g. Gemini)
      3. gen.generation_info["token_usage"] / ["usage"]    (older/rare providers)
    We check all three so this works regardless of which provider is active.

    IMPORTANT: exactly ONE instance of this class must be shared for the whole
    pipeline run (bound at model-construction time AND passed into agent.invoke's
    config). Two separate instances would each independently see every call and
    double the cumulative totals -- see build_awis_agent()/run_pipeline().
    """
    def __init__(self):
        super().__init__()
        self.provider_label = None
        self.model_name = None
        self.call_count = 0
        self.cumulative_prompt_tokens = 0
        self.cumulative_completion_tokens = 0
        self.cumulative_total_tokens = 0
        self._pending_inputs = {}  # run_id -> input snippet, set in on_chat_model_start

        self.log_dir = os.path.abspath("./workspace/logs")
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_path = os.path.join(
            self.log_dir, f"llm_calls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        )

        # --- Code-layer raw-capture (replaces Researcher manually transcribing
        # tool output into raw/research_raw.md -- see on_tool_start/on_tool_end/
        # on_tool_error below). Scoped to AWIS_TOOL_REGISTRY (domain tools only)
        # so filesystem tools (read_file/write_file/ls/grep), write_todos, and
        # task() never get captured -- this both avoids noise and rules out any
        # risk of the capture-writer recursively reacting to its own or another
        # subagent's filesystem writes.
        self._captured_tool_names = {t.name for t in AWIS_TOOL_REGISTRY}
        self._pending_tool_calls = {}  # run_id -> {"name", "input", "timestamp"}
        self.raw_capture_path = os.path.abspath("./workspace/raw/research_raw.md")
        # Cap for the audit-trail capture. Deliberately much larger than
        # truncate_tool_output's ~1200-2000 char cap: that cap protects what the
        # LLM sees inline mid-conversation; this one is Verifier's ground-truth
        # record and needs to actually hold enough to audit against. 20000 chars
        # (~5000 tokens) comfortably covers the largest raw payloads any single
        # tool call in this codebase can return (extractor char_limits top out at
        # 12000) with headroom, while still bounding worst-case file growth
        # across a run with many tool calls.
        self.RAW_CAPTURE_CHAR_CAP = 20000

    def configure(self, provider_label: str, model_name: str) -> None:
        """Called once by build_production_llm() once the active provider is known."""
        self.provider_label = provider_label
        self.model_name = model_name

    def on_tool_start(self, serialized, input_str, *, run_id=None, **kwargs):
        name = serialized.get("name") if isinstance(serialized, dict) else str(serialized)
        print(f"\n🔧 [LIVE TOOL EXECUTION] Executing Tool: '{name}'", flush=True)
        print(f"   └─ Parameters : {input_str}\n", flush=True)

        # Only track domain tools (AWIS_TOOL_REGISTRY) for raw capture. Filesystem
        # tools, write_todos, and task() are deliberately excluded.
        if run_id is not None and name in self._captured_tool_names:
            self._pending_tool_calls[str(run_id)] = {
                "name": name,
                "input": input_str,
                "timestamp": datetime.now().isoformat(),
            }

    def _write_tool_capture(self, run_id, result_text: str) -> None:
        pending = self._pending_tool_calls.pop(str(run_id), None)
        if pending is None:
            # Not a domain tool call (or already popped) -- nothing to capture.
            return

        if len(result_text) > self.RAW_CAPTURE_CHAR_CAP:
            result_text = (
                result_text[: self.RAW_CAPTURE_CHAR_CAP]
                + f"\n... [capture truncated at {self.RAW_CAPTURE_CHAR_CAP} chars, "
                f"original {len(result_text)} chars]"
            )

        # Same block format Researcher used to hand-write, so Verifier's prompt
        # (and anyone reading raw/research_raw.md) needs no format changes.
        block = (
            f"Tool: {pending['name']}\n"
            f"Args: {pending['input']}\n"
            f"Timestamp: {pending['timestamp']}\n"
            f"Result: {result_text}\n\n"
        )
        try:
            os.makedirs(os.path.dirname(self.raw_capture_path), exist_ok=True)
            with open(self.raw_capture_path, "a", encoding="utf-8") as f:
                f.write(block)
        except Exception as e:
            print(f"WARNING: could not write tool capture record: {e}", flush=True)

    def on_tool_end(self, output, *, run_id=None, **kwargs):
        # `output` is whatever the tool function returned -- the complete,
        # unmodified value, never touched by an LLM. This is what makes the
        # capture reliable regardless of model strength.
        self._write_tool_capture(run_id, str(output))

    def on_tool_error(self, error, *, run_id=None, **kwargs):
        # Capture failures too -- a failed tool call is part of what Researcher
        # actually saw and reacted to, and useful for Verifier's fidelity audit.
        self._write_tool_capture(run_id, f"ERROR: {error}")

    def on_chat_model_start(self, serialized, messages, *, run_id, **kwargs):
        # Capture what triggered this specific call so we can report it in on_llm_end,
        # matched via run_id (LangChain guarantees the same run_id on start and end).
        snippet = "N/A"
        try:
            last_msg = messages[0][-1]
            content = last_msg.content
            text = content if isinstance(content, str) else str(content)
            text = re.sub(r'\s+', ' ', text).strip()
            snippet = (text[:160] + "...") if len(text) > 160 else text
        except Exception:
            pass
        self._pending_inputs[str(run_id)] = snippet

    def _resolve_model_name(self, response, kwargs) -> str:
        llm_output = getattr(response, "llm_output", None) or {}
        if isinstance(llm_output, dict):
            for key in ("model_name", "model"):
                if llm_output.get(key):
                    return llm_output[key]
        invocation_params = kwargs.get("invocation_params") or {}
        if invocation_params.get("model"):
            return invocation_params["model"]
        return self.model_name or "unknown"

    def _resolve_usage(self, response):
        llm_output = getattr(response, "llm_output", None) or {}
        if isinstance(llm_output, dict):
            usage = llm_output.get("token_usage") or llm_output.get("usage")
            if usage:
                return dict(usage)

        for generations in response.generations:
            for gen in generations:
                msg = getattr(gen, "message", None)
                usage_metadata = getattr(msg, "usage_metadata", None) if msg else None
                if usage_metadata:
                    return {
                        "prompt_tokens": usage_metadata.get("input_tokens"),
                        "completion_tokens": usage_metadata.get("output_tokens"),
                        "total_tokens": usage_metadata.get("total_tokens"),
                    }
                info = getattr(gen, "generation_info", None) or {}
                usage = info.get("token_usage") or info.get("usage")
                if usage:
                    return dict(usage)
        return None

    def _resolve_tool_calls(self, response):
        names = []
        for generations in response.generations:
            for gen in generations:
                msg = getattr(gen, "message", None)
                tool_calls = getattr(msg, "tool_calls", None) if msg else None
                if tool_calls:
                    for tc in tool_calls:
                        name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                        if name:
                            names.append(name)
        return names

    def on_llm_end(self, response, *, run_id=None, **kwargs):
        self.call_count += 1
        model_used = self._resolve_model_name(response, kwargs)
        label = f" [{self.provider_label}]" if self.provider_label else ""
        input_snippet = self._pending_inputs.pop(str(run_id), "N/A")
        tools_requested = self._resolve_tool_calls(response)
        usage = self._resolve_usage(response)

        prompt_tok = compl_tok = total_tok = None
        if usage:
            prompt_tok = usage.get("prompt_tokens") or usage.get("prompt_eval_count") or usage.get("input_tokens")
            compl_tok = usage.get("completion_tokens") or usage.get("eval_count") or usage.get("output_tokens")
            total_tok = usage.get("total_tokens")
            if not total_tok and isinstance(prompt_tok, int) and isinstance(compl_tok, int):
                total_tok = prompt_tok + compl_tok
            if isinstance(prompt_tok, int):
                self.cumulative_prompt_tokens += prompt_tok
            if isinstance(compl_tok, int):
                self.cumulative_completion_tokens += compl_tok
            if isinstance(total_tok, int):
                self.cumulative_total_tokens += total_tok

        tools_str = ", ".join(tools_requested) if tools_requested else "none"

        print(f"\n{'─' * 60}", flush=True)
        print(f"⚡ LLM Call #{self.call_count}  |  Model: {model_used}{label}", flush=True)
        print(f"   ├─ Input (triggered by) : \"{input_snippet}\"", flush=True)
        print(f"   ├─ Tools requested      : {tools_str}", flush=True)
        print(
            f"   ├─ Tokens (this call)   : prompt={prompt_tok or 'N/A'}, "
            f"completion={compl_tok or 'N/A'}, total={total_tok or 'N/A'}",
            flush=True,
        )
        print(
            f"   └─ Tokens (cumulative)  : prompt={self.cumulative_prompt_tokens}, "
            f"completion={self.cumulative_completion_tokens}, total={self.cumulative_total_tokens}",
            flush=True,
        )
        print(f"{'─' * 60}\n", flush=True)

        record = {
            "call_number": self.call_count,
            "timestamp": datetime.now().isoformat(),
            "provider": self.provider_label,
            "model": model_used,
            "input_snippet": input_snippet,
            "tools_requested": tools_requested,
            "prompt_tokens": prompt_tok,
            "completion_tokens": compl_tok,
            "total_tokens": total_tok,
            "cumulative_prompt_tokens": self.cumulative_prompt_tokens,
            "cumulative_completion_tokens": self.cumulative_completion_tokens,
            "cumulative_total_tokens": self.cumulative_total_tokens,
        }
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            print(f"WARNING: could not write LLM call log record: {e}", flush=True)


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
    Catches Groq HTTP 400 failed_generation exceptions and converts them into valid tool calls!
    """
    def _generate(self, messages, **kwargs):
        trimmed_messages = _strip_orphaned_tool_messages(message_trimmer.invoke(messages))
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

    async def _agenerate(self, messages, **kwargs):
        # Mirrors the sync path above -- LangGraph/deepagents can invoke async
        # under the hood, and without this override the trimmer would silently
        # not apply whenever that path is taken.
        trimmed_messages = _strip_orphaned_tool_messages(message_trimmer.invoke(messages))
        return await super()._agenerate(trimmed_messages, **kwargs)


class TrimmedChatOpenAI(ChatOpenAI):
    """
    Plain ChatOpenAI is used for THREE different providers here (NVIDIA NIM,
    GitHub Models, OpenRouter), and none of them were getting message_trimmer
    applied -- only ToolParsingChatGroq (Groq-only) called it. That means every
    other provider sends the FULL, ever-growing message history on every call
    with no cap at all.

    This was directly visible in a real run: prompt tokens climbed 5451 -> 5544
    -> 5634 -> ... -> 6145 across a single run that never even reached the
    Researcher stage -- each wasted round-trip (hallucinated subagent names,
    repeated write_todos calls) made every subsequent call more expensive too,
    compounding the slowdown instead of staying flat.

    This subclass applies the exact same trimming Groq already had, so context
    size is capped regardless of which provider in the fallback chain is active.
    """
    def _generate(self, messages, **kwargs):
        trimmed_messages = _strip_orphaned_tool_messages(message_trimmer.invoke(messages))
        return super()._generate(trimmed_messages, **kwargs)

    async def _agenerate(self, messages, **kwargs):
        trimmed_messages = _strip_orphaned_tool_messages(message_trimmer.invoke(messages))
        return await super()._agenerate(trimmed_messages, **kwargs)


def _announce_provider(provider_label: str, model_name: str) -> None:
    print(f"\n🤖 Active LLM Provider : {provider_label}  |  Model : {model_name}\n", flush=True)


def build_production_llm(token_logger: "TokenLoggerCallback"):
    # 0. New: OpenAI direct (gpt-5-nano) -- placed FIRST so it's actually used now that
    #    OPENAI_API_KEY is already set in .env. NOTE: gpt-5-nano is a reasoning model and
    #    its API rejects any non-default `temperature` value (400 error), so it is
    #    deliberately omitted here unlike every other branch below.
    #
    #    reasoning_effort: gpt-5-nano supports minimal/low/medium/high (default medium if
    #    omitted). Confirmed live that single write_todos/task calls were routinely burning
    #    4,000-9,000+ completion tokens on purely mechanical steps (updating a todo list,
    #    writing a one-paragraph task description) -- that's reasoning tokens spent on work
    #    that needs none, and it directly feeds the message_trimmer pressure documented above
    #    (bigger completions -> bigger history -> orchestrator's own step-tracking gets
    #    evicted sooner). Passed as a top-level kwarg, not via model_kwargs -- confirmed live
    #    that the installed langchain-openai version recognizes reasoning_effort as a proper
    #    field (model_kwargs triggered "should be specified explicitly" warnings on every call).
    #    Deliberately defaulting to "low", not "minimal": OpenAI's docs confirm minimal
    #    disables parallel tool calling, and Researcher relies on firing several search tools
    #    in parallel per turn -- "minimal" would silently serialize (and likely break) that.
    #    Override with OPENAI_REASONING_EFFORT=minimal|low|medium|high in .env to tune further.
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        model_name = os.getenv("OPENAI_MODEL", "gpt-5-nano")
        reasoning_effort = os.getenv("OPENAI_REASONING_EFFORT", "low")
        _announce_provider("OpenAI", model_name)
        token_logger.configure(provider_label="OpenAI", model_name=model_name)
        return TrimmedChatOpenAI(
            model=model_name,
            openai_api_key=openai_key,
            reasoning_effort=reasoning_effort,
            max_retries=5,
            callbacks=[token_logger]
        )

    # 1. Primary Option: NVIDIA NIM API (meta/llama-3.1-70b-instruct)
    nvidia_key = os.getenv("NVIDIA_API_KEY")
    if nvidia_key:
        model_name = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")
        _announce_provider("NVIDIA NIM", model_name)
        token_logger.configure(provider_label="NVIDIA NIM", model_name=model_name)
        return TrimmedChatOpenAI(
            model=model_name,
            openai_api_key=nvidia_key,
            openai_api_base="https://integrate.api.nvidia.com/v1",
            temperature=0.0,
            max_retries=5,
            callbacks=[token_logger]
        )

    # 2. Secondary Option: Groq LPU
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        _validate_groq_model(model_name, groq_key)
        _announce_provider("Groq", model_name)
        token_logger.configure(provider_label="Groq", model_name=model_name)
        return ToolParsingChatGroq(
            model_name=model_name,
            groq_api_key=groq_key,
            temperature=0.0,
            max_retries=5,
            callbacks=[token_logger]
        )

    gh_token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if gh_token:
        model_name = os.getenv("GITHUB_MODEL", "gpt-4o-mini")
        _announce_provider("GitHub Models", model_name)
        token_logger.configure(provider_label="GitHub Models", model_name=model_name)
        return TrimmedChatOpenAI(
            model=model_name,
            openai_api_key=gh_token,
            openai_api_base="https://models.inference.ai.azure.com",
            temperature=0.0,
            max_retries=5,
            callbacks=[token_logger]
        )

    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            class TrimmedChatGoogleGenerativeAI(ChatGoogleGenerativeAI):
                """Same trimming treatment as TrimmedChatOpenAI, for the Gemini fallback path."""
                def _generate(self, messages, **kwargs):
                    trimmed_messages = _strip_orphaned_tool_messages(message_trimmer.invoke(messages))
                    return super()._generate(trimmed_messages, **kwargs)

                async def _agenerate(self, messages, **kwargs):
                    trimmed_messages = _strip_orphaned_tool_messages(message_trimmer.invoke(messages))
                    return await super()._agenerate(trimmed_messages, **kwargs)

            model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            _announce_provider("Google Gemini", model_name)
            token_logger.configure(provider_label="Google Gemini", model_name=model_name)
            return TrimmedChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=gemini_key,
                temperature=0.0,
                max_retries=5,
                callbacks=[token_logger]
            )
        except ImportError:
            pass

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        model_name = os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-72b-instruct")
        _announce_provider("OpenRouter", model_name)
        token_logger.configure(provider_label="OpenRouter", model_name=model_name)
        return TrimmedChatOpenAI(
            model=model_name,
            openai_api_key=openrouter_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.0,
            max_retries=5,
            callbacks=[token_logger]
        )

    raise ValueError("No valid API key found in environment variables.")


def build_awis_agent(query: str = "Agentic AI Architectures", token_logger: "TokenLoggerCallback" = None):
    vfs_path = os.path.abspath("./workspace")
    reports_path = os.path.abspath("./workspace/reports")
    raw_path = os.path.abspath("./workspace/raw")
    os.makedirs(vfs_path, exist_ok=True)
    os.makedirs(reports_path, exist_ok=True)
    os.makedirs(raw_path, exist_ok=True)

    if token_logger is None:
        token_logger = TokenLoggerCallback()

    llm = build_production_llm(token_logger)
    backend = FilesystemBackend(root_dir=vfs_path, virtual_mode=True)
    dynamic_research_tools = select_dynamic_tools(query, max_tools=2)

    agent = create_deep_agent(
        model=llm,
        backend=backend,
        tools=[],
        system_prompt=(
            f"Lead Orchestrator for AWIS. TOPIC: '{query}'.\n\n"
            "Run these 4 stages in this exact order, one at a time:\n"
            "1. Delegate to Planner. It writes raw/plan.md.\n"
            "2. Delegate to Researcher. Tell it to read raw/plan.md and cover all 4 "
            "dimensions in it. It writes raw/research.md.\n"
            "3. Delegate to Verifier. Tell it to read raw/research.md and write raw/verified.md.\n"
            "4. Delegate to Reporter. Tell it to read raw/research.md and raw/verified.md, "
            "then call save_intelligence_report.\n\n"
            "Do not skip a stage. Do not do research or writing yourself — only delegate.\n"
            "As soon as Reporter finishes, return its report as your final answer and stop."        ),
        subagents=[
            {
                "name": "Planner",
                "description": "Creates structured multi-domain research plan.",
                "system_prompt": (
                    f"TOPIC: '{query}'.\n\n"
                    "Write a short 4-part research plan covering: Academic, Web/Wiki, "
                    "Developer code, Community opinion.\n"
                    "Call write_file to save it as raw/plan.md.\n"
                    "Then return the plan as your final message."
                ),
                "tools": [],
            },
            {
                "name": "Researcher",
                "description": "Gathers raw data across specialized tools.",
                "system_prompt": (
                    f"TOPIC: '{query}'.\n\n"
                    "1. Call read_file on raw/plan.md.\n"
                    "2. Use your tools to research all 4 parts of the plan: Academic, "
                    "Web/Wiki, Developer code, Community opinion.\n"
                    "3. Write everything you found — facts, dates, paper links, repo "
                    "links - as well as a summary conclusion of your findings — to raw/research.md using write_file.\n"
                    "4. Return the short summary as your final message. \n\n"
                    "Only call one tool at a time, wait for it to finish, then call the next. Do not call tools in parallel."
                    "If a tool fails, skip it and keep going with the others."
                ),
                "tools": dynamic_research_tools,
            },
            {
                "name": "Verifier",
                "description": "Audits Researcher's synthesis for fidelity to the raw retrieved data (no search tools).",
                "system_prompt": (
                    f"TOPIC: '{query}'.\n\n"
                    "1. Call read_file on raw/research_raw.md (the unedited record of "
                    "every tool call Researcher made).\n"
                    "2. Call read_file on raw/research.md (Researcher's write-up).\n"
                    "3. Check every claim, number, date, and link in research.md actually "
                    "appears in research_raw.md. Flag anything unsupported, exaggerated, "
                    "or missing a source.\n"
                    "4. Check all 4 plan dimensions are covered.\n\n"
                    "You have no search tools — do not research anything new, just check "
                    "for fidelity to research_raw.md.\n\n"
                    "Call write_file to save your findings as raw/verified.md. Then "
                    "return them as your final message."
                    "Only call one tool at a time, wait for it to finish, then call the next. Do not call tools in parallel."
                ),
                "tools": VERIFIER_TOOLS,
            },
            {
                "name": "Reporter",
                "description": "Synthesizes final comprehensive intelligence brief.",
                "system_prompt": (
                    f"TOPIC: '{query}'.\n\n"
                    "1. Call read_file on raw/research.md. after getting its content, "
                    "call read_file on raw/verified.md. Base your "
                    "report only on these two files.\n"
                    "2. Write a report with these 6 sections, using real facts, dates, "
                    "paper links, and repo links from the files:\n"
                    "1. Executive Summary & Core Insights\n"
                    "2. Technical Architecture & Workflows\n"
                    "3. Code Patterns & GitHub Repositories (with links)\n"
                    "4. Benchmark & Paper Audit (with arXiv links)\n"
                    "5. Risks & Trade-offs\n"
                    "6. Verified Source Citation Index\n"
                    "3. Call save_intelligence_report ONCE with the full report.\n\n"
                    "Once save_intelligence_report succeeds, stop — do not call it again "
                    "and do not keep editing."
                    "Only call one tool at a time, wait for it to finish, then call the next. Do not call tools in parallel."

                ),
                "tools": REPORTER_TOOLS,
            },
        ],
    )
    return agent


def _clear_raw_dir() -> None:
    """
    Clears workspace/raw/ (plan.md, research.md, research_raw.md, verified.md)
    at the end of a run so the next run starts clean, without relying on the
    reactive "already exists, stop" guards in each subagent's prompt. Only
    files directly inside raw/ are removed -- workspace/reports/ (where
    save_intelligence_report writes) is untouched.
    """
    raw_path = os.path.abspath("./workspace/raw")
    if not os.path.isdir(raw_path):
        return
    for entry in os.listdir(raw_path):
        entry_path = os.path.join(raw_path, entry)
        try:
            if os.path.isfile(entry_path):
                os.remove(entry_path)
        except Exception as e:
            print(f"WARNING: could not clear '{entry_path}': {e}", flush=True)


def run_pipeline(raw_query: str) -> str:
    clean_query = re.sub(r'\s+', ' ', raw_query).strip()
    if not clean_query:
        return "Error: Empty query provided."

    # Clear workspace/raw/ (plan.md, research.md, research_raw.md, verified.md)
    # at the START of each run, before anything else happens. This replaces the
    # reactive "already exists, stop" guards in each subagent's prompt with a
    # proper fix, and -- unlike clearing at the end -- leaves a failed run's
    # raw/ files on disk for inspection right up until the next run actually
    # starts, instead of wiping them the moment the failed run finishes.
    _clear_raw_dir()

    stats = cache_manager.get_stats()
    print("=" * 60)
    print("       AWIS Production Web Intelligence Pipeline            ")
    print("=" * 60)
    print(f"Target Query : '{clean_query}'")
    print(f"Cache Volume : {stats['total_entries']} entries ({stats['size_bytes'] / 1024:.1f} KB)")
    print()

    token_logger = TokenLoggerCallback()
    agent = build_awis_agent(clean_query, token_logger=token_logger)

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

    for attempt in range(1, max_attempts + 1):
        try:
            # Reuse the SAME token_logger instance created above -- do not construct
            # a second TokenLoggerCallback here, or cumulative totals would be counted twice.
            response = agent.invoke(
                {"messages": [{"role": "user", "content": clean_query}]},
                config={"recursion_limit": 80, "callbacks": [token_logger]},
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
    print(f"Latest Report : {latest_file}")
    print(f"Total LLM Calls    : {token_logger.call_count}")
    print(f"Total Tokens Used  : {token_logger.cumulative_total_tokens} "
          f"(prompt={token_logger.cumulative_prompt_tokens}, completion={token_logger.cumulative_completion_tokens})")
    print(f"Per-call Log (JSONL): {token_logger.log_path}\n")

    return final_output


if __name__ == "__main__":
    query_arg = sys.argv[1] if len(sys.argv) > 1 else "Latest advances in Agentic AI architectures"
    run_pipeline(query_arg)