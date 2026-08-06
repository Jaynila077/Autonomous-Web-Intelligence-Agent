import os
import re
import sys
import asyncio
import logging
from datetime import datetime

import nest_asyncio
nest_asyncio.apply()

from src.core.agent import build_awis_agent
from src.core.llm import TokenLoggerCallback
from src.tools.cache_manager import cache_manager
from src.core.guardrails_wrapper import NeMoGuardrailsService

logger = logging.getLogger(__name__)

_guardrails_service = None

def _get_guardrails() -> NeMoGuardrailsService:
    global _guardrails_service
    if _guardrails_service is None:
        _guardrails_service = NeMoGuardrailsService(config_dir="config")
    return _guardrails_service

def run_pipeline(raw_query: str, user_id: str = "default", job_id: str = "default") -> str:
    clean_query = re.sub(r'\s+', ' ', raw_query).strip()
    if not clean_query:
        return "Error: Empty query provided."

    # 1. Pre-flight NeMo Guardrails check (Jailbreak, Off-topic, PII redaction)
    input_check = asyncio.run(_get_guardrails().check_input_rails(clean_query))

    if input_check.status == "blocked_input":
        print("\n" + "=" * 60)
        print("         [SECURITY GUARDRAIL TRIGGERED - REQUEST BLOCKED]")
        print("=" * 60)
        print(f"Reason   : {input_check.blocked_reason}")
        print(f"Response : {input_check.response}\n")
        return input_check.response

    # Use sanitized query if PII was redacted
    if input_check.status == "pii_redacted":
        clean_query = input_check.sanitized_prompt

    stats = cache_manager.get_stats()

    print("=" * 60)
    print("      AWIS Production Web Intelligence Pipeline            ")
    print("=" * 60)
    print(f"Target Query : '{clean_query}'")
    print(f"Cache Volume : {stats['total_entries']} entries ({stats['size_bytes'] / 1024:.1f} KB)")
    print()

    agent, vfs_path = build_awis_agent(clean_query, user_id=user_id, job_id=job_id)

    def _looks_like_leaked_tool_call(text: str) -> bool:
        stripped = text.strip()
        if "# Executive Summary" in stripped or "# Technical Analysis" in stripped or "# Intelligence Report" in stripped:
            return False
        return (stripped.startswith('{"type": "function"') or stripped.startswith("{'type': 'function'")) and not stripped.endswith("}")

    # Job-scoped latest_report.md, matching build_awis_agent's isolated vfs_path
    latest_file = os.path.join(vfs_path, "latest_report.md")
    if os.path.exists(latest_file):
        try:
            os.remove(latest_file)
        except Exception as e:
            logger.warning(f"[Handled] {e}")

    max_attempts = 3
    final_output = None
    last_error = None

    token_logger = TokenLoggerCallback()
    callbacks_list = [token_logger]
    langfuse_handler = None

    # 2. Langfuse Observability Integration
    try:
        pub_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        sec_key = os.getenv("LANGFUSE_SECRET_KEY")
        host_url = os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL") or "https://cloud.langfuse.com"

        if pub_key and sec_key:
            try:
                from langfuse.langchain import CallbackHandler
                langfuse_handler = CallbackHandler()
            except (ImportError, TypeError):
                from langfuse.callback import CallbackHandler
                langfuse_handler = CallbackHandler(
                    public_key=pub_key,
                    secret_key=sec_key,
                    host=host_url,
                )
            callbacks_list.append(langfuse_handler)
            print(f"[Langfuse Observability] Tracing Active -> Host: {host_url}")
        else:
            print("[Langfuse] Tracing disabled: missing LANGFUSE_PUBLIC_KEY/SECRET_KEY in .env")
    except Exception as e:
        print(f"[Langfuse Warning] Failed to initialize tracing: {e}")

    for attempt in range(1, max_attempts + 1):
        try:
            response = agent.invoke(
                {"messages": [{"role": "user", "content": clean_query}]},
                config={"recursion_limit": 50, "callbacks": callbacks_list},
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

    # 3. Post-flight NeMo Guardrails check (Toxicity, PII masking)
    output_check = asyncio.run(_get_guardrails().check_output_rails(output=final_output))
    if output_check.status == "blocked_output":
        print("\n" + "=" * 60)
        print("         [OUTPUT GUARDRAIL TRIGGERED - RESPONSE BLOCKED]")
        print("=" * 60)
        print(f"Reason   : {output_check.blocked_reason}")
        print(f"Response : {output_check.response}\n")
        return output_check.response

    final_output = output_check.response

    # 4. Report Saving — job-scoped, matching build_awis_agent's isolated vfs_path
    ws_reports_dir = os.path.join(vfs_path, "reports")
    os.makedirs(ws_reports_dir, exist_ok=True)

    slug = re.sub(r'[^a-zA-Z0-9]+', '_', clean_query.strip().lower()).strip('_')[:30]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{slug}_{timestamp}.md"

    ws_filepath = os.path.join(ws_reports_dir, filename)

    with open(ws_filepath, "w", encoding="utf-8") as f:
        f.write(final_output)
    with open(latest_file, "w", encoding="utf-8") as f:
        f.write(final_output)

    print("\n" + "=" * 60)
    print("                FINAL INTELLIGENCE REPORT                ")
    print("=" * 60 + "\n")
    print(final_output)
    print("\n" + "=" * 60)
    print(f"Latest Report : {latest_file}")
    print(f"Saved Report  : {ws_filepath}\n")

    # Flush async traces to Langfuse before returning
    if langfuse_handler:
        try:
            langfuse_handler.flush()
        except Exception as e:
            logger.warning(f"[Handled] {e}")

    return final_output

if __name__ == "__main__":
    query_arg = sys.argv[1] if len(sys.argv) > 1 else "Latest advances in Agentic AI architectures"
    run_pipeline(query_arg)