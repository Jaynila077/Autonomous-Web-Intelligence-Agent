import os
from typing import List, Optional
from pydantic import BaseModel


from planner import planner_node

class AgentState(BaseModel):
    original_query: str
    plan: Optional[List[str]] = []

def get_mock_state() -> AgentState:
    return AgentState(
        original_query="Investigate the recent security vulnerabilities and compliance issues associated with deploying open-source LLMs in enterprise cloud environments."
    )


if __name__ == "__main__":

    if not os.environ.get("GROQ_API_KEY"):
        print("ERROR: Please set your GROQ_API_KEY environment variable.")
        exit(1)

    print("Initializing mock AgentState...")
    state = get_mock_state()

    print(f"Original Query: {state.original_query}")
    print("\nRunning Planner Node (Calling Groq API)...")

  
    state_update = planner_node(state)


    generated_plan = state_update.get("plan", [])

    print("\n--- GENERATED PLAN (SUB-TASKS) ---\n")
    if generated_plan:
        for idx, task in enumerate(generated_plan, 1):
            print(f"[{idx}] {task}")
    else:
        print("FAILED: No sub-tasks were generated.")
    print("\n-----------------------------------\n")

    print("Test Complete.")