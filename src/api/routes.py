from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from src.core.orchestrator import build_awis_agent

router = APIRouter()

class QueryRequest(BaseModel):
    query: str

@router.post("/query")
async def execute_query(request: QueryRequest, background_tasks: BackgroundTasks):
    """Submits a research query to the DeepAgent pipeline."""
    agent = build_awis_agent()
    # Execute agent in background task
    background_tasks.add_task(agent.run, request.query)
    return {"status": "processing", "message": f"Query submitted: {request.query}"}

@router.get("/report")
async def get_latest_report():
    """Reads the generated report from the Virtual Filesystem workspace."""
    try:
        with open("./workspace/final_report.md", "r") as f:
            content = f.read()
        return {"report": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Report not generated yet.")
