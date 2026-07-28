import sys
import os
from dotenv import load_dotenv

load_dotenv()

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_groq import ChatGroq
from src.tools.registry import AWIS_TOOL_REGISTRY

def build_awis_agent():
    vfs_path = os.path.abspath("./workspace")
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
    return agent

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "Latest engineering challenges with vector databases"
    
    print(f"\nInitializing AWIS DeepAgent Pipeline...")
    print(f"Target Query: '{query}'\n")
    
    awis_agent = build_awis_agent()
    print("Running agent workflow...")
    
    response = awis_agent.invoke({"messages": [{"role": "user", "content": query}]})
    
    print("\nPipeline Execution Finished!")
    print(f"Check the './workspace/' folder for generated markdown reports.")