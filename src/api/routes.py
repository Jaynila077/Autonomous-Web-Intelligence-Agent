import os
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from src.core.main import build_awis_agent

router = APIRouter()

REPORT_PATH = "./workspace/final_report.md"


class QueryRequest(BaseModel):
    query: str


def run_agent_task(query: str):
    """Background worker triggered by POST /api/v1/query"""
    os.makedirs("./workspace", exist_ok=True)
    
    # Remove stale reports from previous runs
    report_path = "./workspace/final_report.md"
    if os.path.exists(report_path):
        os.remove(report_path)

    # Initialize agent and invoke with standard MessagesState
    awis_agent = build_awis_agent()
    awis_agent.invoke({"messages": [{"role": "user", "content": query}]})


@router.post("/query")
def start_query(request: QueryRequest, background_tasks: BackgroundTasks):
    """Triggers the autonomous RAG/OSINT pipeline in the background."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    background_tasks.add_task(run_agent_task, request.query)
    return {"status": "started", "message": "Agent pipeline initiated."}


@router.get("/report")
def get_report():
    """Checks if the report is ready and returns the Markdown content."""
    if not os.path.exists(REPORT_PATH):
        return {"status": "processing", "content": None}

    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    return {"status": "completed", "content": content}