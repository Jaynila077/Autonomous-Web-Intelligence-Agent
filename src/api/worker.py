import os
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any

from core.main import build_awis_agent
from src.api.schemas import JobStatus

job_state_store: Dict[str, Dict[str, Any]] = {}

def _sync_pipeline_runner(user_id: str, job_id: str, query: str) -> str:
    """
    Synchronous wrapper that imports and invokes the agent pipeline from core/main.py.
    """
    agent, vfs_path = build_awis_agent(user_id=user_id, job_id=job_id)
    agent.invoke({"messages": [{"role": "user", "content": query}]})
    return os.path.join(vfs_path, "final_report.md")

async def execute_agent_pipeline(job_id: str, user_id: str, query: str):
    """
    Asynchronous background task that runs the AWIS pipeline off the main event loop.
    """
    now = datetime.now(timezone.utc)
    job_state_store[job_id] = {
        "job_id": job_id,
        "user_id": user_id,
        "status": JobStatus.PLANNING,
        "current_agent": "Planner",
        "report_url": None,
        "error_message": None,
        "created_at": now,
        "updated_at": now
    }

    try:
        job_state_store[job_id]["status"] = JobStatus.RESEARCHING
        job_state_store[job_id]["current_agent"] = "Researcher"
        job_state_store[job_id]["updated_at"] = datetime.now(timezone.utc)

        report_path = await asyncio.to_thread(_sync_pipeline_runner, user_id, job_id, query)

        if not os.path.exists(report_path):
            raise FileNotFoundError(f"Expected report at {report_path}, but file was not created.")

        job_state_store[job_id].update({
            "status": JobStatus.COMPLETED,
            "current_agent": "Reporter",
            "report_path": report_path,
            "report_url": f"/api/v1/queries/{job_id}/report",
            "updated_at": datetime.now(timezone.utc)
        })

    except Exception as exc:
        job_state_store[job_id].update({
            "status": JobStatus.FAILED,
            "current_agent": None,
            "error_message": str(exc),
            "updated_at": datetime.now(timezone.utc)
        })