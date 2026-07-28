import os
from deepagents import create_deep_agent, FilesystemBackend
from src.tools.registry import AWIS_TOOL_REGISTRY

def build_awis_agent():
    
    vfs_path = os.path.abspath("./workspace")
    
    agent = create_deep_agent(
        backend=FilesystemBackend(workspace_dir=vfs_path),
        tools=AWIS_TOOL_REGISTRY,
        subagents=[
            {
                "name": "Planner",
                "role": "Break down the user query into a step-by-step intelligence plan using TodoToolset."
            },
            {
                "name": "Researcher",
                "role": "Use discovery and extraction tools to gather data. Save raw markdown files directly to the filesystem."
            },
            {
                "name": "Verifier",
                "role": "Read saved markdown files, perform a grounding audit, extract atomic facts, and save verified_claims.json."
            },
            {
                "name": "Reporter",
                "role": "Read verified_claims.json and compile the final Markdown report to workspace/final_report.md."
            }
        ]
    )
    return agent
