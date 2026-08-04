# src/core/main.py
import sys
import os
import time
from dotenv import load_dotenv

load_dotenv()

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_groq import ChatGroq
from src.tools.registry import AWIS_TOOL_REGISTRY


class MockAWISAgent:
    """
    Lightweight drop-in replacement for DeepAgent pipeline during test/mock runs.
    Calls a fast, cheap LLM if GROQ_API_KEY is present; otherwise falls back to local echo.
    Always writes `final_report.md` to `vfs_path`.
    """

    def __init__(self, vfs_path: str):
        self.vfs_path = vfs_path

    def invoke(self, input_dict: dict) -> dict:
        messages = input_dict.get("messages", [])
        user_query = "Unknown query"
        if messages and isinstance(messages, list):
            user_query = messages[-1].get("content", user_query)

        groq_api_key = os.getenv("GROQ_API_KEY")

        if groq_api_key:
            try:
                # Fast, cheap Groq LLM model call
                llm = ChatGroq(
                    model_name="llama-3.1-8b-instant",
                    temperature=0.1,
                    max_tokens=200,
                    groq_api_key=groq_api_key,
                )
                prompt = (
                    f"You are a brief research assistant. Summarize this query into a "
                    f"short markdown intelligence brief: '{user_query}'"
                )
                response = llm.invoke(prompt)
                report_content = (
                    f"# Mock Intelligence Brief\n\n"
                    f"**Query:** {user_query}\n\n"
                    f"## LLM Summary\n{response.content}\n"
                )
            except Exception as e:
                report_content = (
                    f"# Mock Intelligence Brief (Fallback)\n\n"
                    f"**Query:** {user_query}\n\n"
                    f"**Status:** LLM call attempted but failed ({str(e)}). Fallback executed.\n"
                )
        else:
            # Fallback when zero API keys are set
            # -------------------------------------------------------------------------
            # TEMP: artificial delay for restart-test purposes, remove after testing
            # -------------------------------------------------------------------------
            time.sleep(8)

            report_content = (
                f"# Mock Intelligence Brief (Local Echo)\n\n"
                f"**Query:** {user_query}\n\n"
                f"This report was generated locally without an external LLM API key.\n"
            )

        # Write report to isolated workspace folder expected by worker.py
        report_path = os.path.join(self.vfs_path, "final_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        return {"output": "Mock report generated successfully."}


def build_awis_agent(user_id: str = "cli_user", job_id: str = "local_test"):
    """
    Single source of truth for building the AWIS DeepAgent pipeline.
    If MOCK_AGENT env var is set to 'true', returns a fast MockAWISAgent instance.
    """
    vfs_path = os.path.abspath(f"./workspace/users/{user_id}/jobs/{job_id}")
    os.makedirs(vfs_path, exist_ok=True)

    # Check if Mock Agent is enabled
    is_mock = os.getenv("MOCK_AGENT", "false").lower() in ("true", "1", "yes")

    if is_mock:
        return MockAWISAgent(vfs_path=vfs_path), vfs_path

    # Full Real DeepAgent Pipeline
    llm = ChatGroq(
        model_name="openai/gpt-oss-120b",
        temperature=0.1,
        groq_api_key=os.getenv("GROQ_API_KEY"),
    )

    backend = FilesystemBackend(root_dir=vfs_path, virtual_mode=False)

    agent = create_deep_agent(
        model=llm,
        backend=backend,
        tools=AWIS_TOOL_REGISTRY,
        subagents=[
            {
                "name": "Planner",
                "description": "Breaks down user queries into a step-by-step intelligence plan.",
                "system_prompt": "You are a master planning agent. Break down the user query into clear tasks using TodoToolset.",
            },
            {
                "name": "Researcher",
                "description": "Gathers data using web discovery and extraction tools.",
                "system_prompt": "You are a web intelligence researcher. Use available search and extractor tools, and save raw files to workspace.",
            },
            {
                "name": "Verifier",
                "description": "Audits saved files for factual accuracy and evidence grounding.",
                "system_prompt": "You are a strict verifier agent. Read saved files, cross-examine claims, and compile verified data.",
            },
            {
                "name": "Reporter",
                "description": "Synthesizes final intelligence reports.",
                "system_prompt": "You are a senior report generator. Compile the final intelligence brief into workspace/final_report.md.",
            },
        ],
    )
    return agent, vfs_path


if __name__ == "__main__":
    query = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Latest engineering challenges with vector databases"
    )
    print(f"\nInitializing AWIS DeepAgent Pipeline (CLI Mode)...")
    print(f"Target Query: '{query}'\n")

    awis_agent, vfs_path = build_awis_agent(user_id="cli_test", job_id="debug_run")
    print("Running agent workflow...")

    response = awis_agent.invoke({"messages": [{"role": "user", "content": query}]})
    print("\nPipeline Execution Finished!")
    print(f"Check '{vfs_path}' for generated markdown reports.")