import os
import json
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from scout import scout_node


# ==========================================
# MOCKING SCHEMAS (Strictly for standalone testing)
# ==========================================
class AgentState(BaseModel):
    original_query: str
    plan: List[str]
    scout_metadata: Optional[List[Dict[str, Any]]] = []


# ==========================================
# MOCK DATA INJECTION
# ==========================================
def get_mock_state() -> AgentState:
    return AgentState(
        original_query="Investigate the recent security vulnerabilities and compliance issues associated with deploying open-source LLMs.",
        plan=[
            "Identify top CVE vulnerability disclosures for open-source LLMs in 2023-2024.",
            "Analyze data exfiltration risks and regulatory compliance frameworks for cloud-hosted LLM deployments."
        ]
    )


# ==========================================
# TEST EXECUTION
# ==========================================
if __name__ == "__main__":
    if not os.environ.get("GROQ_API_KEY"):
        print("ERROR: Please set your GROQ_API_KEY environment variable.")
        exit(1)

    print("Initializing mock AgentState for Scout...")
    state = get_mock_state()

    print(f"Loaded Plan ({len(state.plan)} sub-tasks):")
    for item in state.plan:
        print(f"  - {item}")

    print("\nRunning Scout Node (Selecting Tool Scopes & Fetching Metadata)...")
    
    state_update = scout_node(state)
    scout_metadata = state_update.get("scout_metadata", [])

    print("\n--- SCOUT METADATA OUTPUT (JSON) ---\n")
    print(json.dumps(scout_metadata, indent=2))
    print("\n------------------------------------\n")

    print("Test Complete.")