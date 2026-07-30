import os
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from src.core.main import run_pipeline

router = APIRouter()

class QueryRequest(BaseModel):
    query: str

@router.post("/query")
async def execute_query(request: QueryRequest, background_tasks: BackgroundTasks):
    """Submits a research query to the AWIS DeepAgent pipeline."""
    background_tasks.add_task(run_pipeline, request.query)
    return {
        "status": "processing",
        "message": f"Research task submitted to AWIS pipeline: '{request.query}'"
    }

@router.get("/report")
async def get_latest_report():
    """Reads the generated latest report from the Virtual Filesystem workspace."""
    latest_path = os.path.abspath("./workspace/latest_report.md")
    try:
        with open(latest_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"report": content, "filename": "latest_report.md"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No latest report generated yet.")

@router.get("/reports")
async def list_all_reports():
    """Lists all historical reports saved in the workspace/reports directory."""
    reports_dir = os.path.abspath("./workspace/reports")
    if not os.path.exists(reports_dir):
        return {"reports": []}
    
    files = [
        f for f in os.listdir(reports_dir)
        if f.endswith(".md")
    ]
    files.sort(reverse=True)
    return {"reports": files}

@router.get("/reports/{report_name}")
async def get_specific_report(report_name: str):
    """Retrieves the content of a specific historical report."""
    reports_dir = os.path.abspath("./workspace/reports")
    file_path = os.path.join(reports_dir, report_name)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Report '{report_name}' not found.")
        
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"report": content, "filename": report_name}
