import os
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from src.core.main import build_awis_agent

router = APIRouter()

class QueryRequest(BaseModel):
    query: str

def _run_agent_and_save_report(query: str):
    """
    Runs the DeepAgent pipeline synchronously (invoked as a background task)
    and writes the final output to workspace/final_report.md, so that
    GET /report has something to read afterwards.
    """
    agent = build_awis_agent()
    response = agent.invoke({"messages": [{"role": "user", "content": query}]})
    final_output = response["messages"][-1].content

    workspace_dir = os.path.abspath("./workspace")
    os.makedirs(workspace_dir, exist_ok=True)
    report_path = os.path.join(workspace_dir, "final_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(final_output)

@router.post("/query")
async def execute_query(request: QueryRequest, background_tasks: BackgroundTasks):
    """Submits a research query to the DeepAgent pipeline."""
    background_tasks.add_task(_run_agent_and_save_report, request.query)
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