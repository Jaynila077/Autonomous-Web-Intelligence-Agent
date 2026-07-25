import asyncio
from src.schemas.state import AgentState

async def run_pipeline(query: str):
    # Initialize global state
    state = AgentState(
        query_id="req-001",
        original_query=query
    )
    print(f"Initialized pipeline for query: {state.original_query}")
    
    # TODO: Orchestration loop calling Dev 2 -> Dev 3 -> Dev 4 -> Dev 5
    return state

if __name__ == "__main__":
    asyncio.run(run_pipeline("Investigate latest battery supply chain disruptions"))
