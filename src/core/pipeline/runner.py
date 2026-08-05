import os
import re

from src.core.agent import build_awis_agent
from src.core.llm import TokenLoggerCallback
from src.tools.cache_manager import cache_manager


def run_pipeline(raw_query: str) -> str:
    clean_query = re.sub(r'\s+', ' ', raw_query).strip()
    if not clean_query:
        return "Error: Empty query provided."

    stats = cache_manager.get_stats()

    print("=" * 60)
    print("      AWIS Production Web Intelligence Pipeline            ")
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