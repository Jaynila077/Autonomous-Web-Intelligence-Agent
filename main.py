import os
import asyncio
from langgraph.graph import StateGraph, START, END
from schemas.state import AgentState

from agents.planner.planner_agent import planner_node
from agents.scout.scout_agent import scout_node

async def run_pipeline(query: str):
    print(f"Initialized graph pipeline for query: {query}\n")


    workflow = StateGraph(AgentState)


    workflow.add_node("planner", planner_node)
    workflow.add_node("scout", scout_node)

   
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "scout")
    
    # ==========================================
    # TODO: Link Dev 3 (Extractor) -> Dev 4 (Verifier) -> Dev 5 (Reporter)
    # Example: workflow.add_edge("scout", "extractor")
    # ==========================================
    
    workflow.add_edge("scout", END) # Temporary

    app = workflow.compile()

    initial_state = {
        "query_id": "req-001",
        "original_query": query,
        "plan": [],
        "scouted_links": []
    }
    
    print("[Executing LangGraph Workflow...]")
    final_state = await app.ainvoke(initial_state)
    
    return final_state

if __name__ == "__main__":
    if not os.environ.get("GROQ_API_KEY"):
        print("ERROR: GROQ_API_KEY environment variable is missing.")
        exit(1)
        
    target_query = "Investigate latest battery supply chain disruptions"
    result = asyncio.run(run_pipeline(target_query))
    
    print("\n--- FINAL GRAPH STATE ---")
    if result.get("scouted_links"):
        print(f"Success: Harvested {len(result['scouted_links'])} links.")