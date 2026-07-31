import sys
import os
from dotenv import load_dotenv

load_dotenv()

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_groq import ChatGroq
from src.tools.registry import AWIS_TOOL_REGISTRY

def build_awis_agent(user_id: str = "cli_user", job_id: str = "local_test"):
    
    vfs_path = os.path.abspath(f"./workspace/users/{user_id}/jobs/{job_id}")
    os.makedirs(vfs_path, exist_ok=True)
    
    llm = ChatGroq(
        model_name="openai/gpt-oss-120b",
        temperature=0.1,
        groq_api_key=os.getenv("GROQ_API_KEY")
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
                "system_prompt": "You are a master planning agent. Break down the user query into clear tasks using TodoToolset."
            },
            {
                "name": "Researcher",
                "description": "Gathers data using web discovery and extraction tools.",
                "system_prompt": "You are a web intelligence researcher. Use available search and extractor tools, and save raw files to workspace."
            },
            {
                "name": "Verifier",
                "description": "Audits saved files for factual accuracy and evidence grounding.",
                "system_prompt": "You are a strict verifier agent. Read saved files, cross-examine claims, and compile verified data."
            },
            {
                "name": "Reporter",
                "description": "Synthesizes final intelligence reports.",
                "system_prompt": "You are a senior report generator. Compile the final intelligence brief into workspace/final_report.md."
            }
        ]
    )
    return agent, vfs_path

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "Latest engineering challenges with vector databases"
    print(f"\nAWIS DeepAgent Pipeline (CLI Mode)...")
    print(f"Target Query: '{query}'\n")
    
    awis_agent, vfs_path = build_awis_agent(user_id="cli_test", job_id="debug_run")
    print("Running agent workflow...")
    
    response = awis_agent.invoke({"messages": [{"role": "user", "content": query}]})
    print("\nPipeline Execution Finished!")
    print(f"Check '{vfs_path}' for generated markdown reports.")