import os
import asyncio
from datetime import datetime, timezone
from sqlmodel import Session, select

from src.core.main import build_awis_agent
from src.api.schemas import JobStatus
from src.api.database import engine, Job


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
   # 1. Update DB state to PLANNING / RESEARCHING
    with Session(engine) as db:
        job = db.get(Job, job_id)
        if job:
            job.status = JobStatus.RESEARCHING
            job.current_agent = "Researcher"
            job.updated_at = now
            db.add(job)
            db.commit()

    try:
        # 2. Run heavy synchronous agent workflow on background thread
        report_path = await asyncio.to_thread(_sync_pipeline_runner, user_id, job_id, query)

        if not os.path.exists(report_path):
            raise FileNotFoundError(f"Expected report at {report_path}, but file was not created.")

        # 3. Update DB state to COMPLETED
        with Session(engine) as db:
            job = db.get(Job, job_id)
            if job:
                job.status = JobStatus.COMPLETED
                job.current_agent = "Reporter"
                job.report_path = report_path
                job.report_url = f"/api/v1/queries/{job_id}/report"
                job.updated_at = datetime.now(timezone.utc)
                db.add(job)
                db.commit()

    except Exception as exc:
        # 4. Handle errors gracefully in DB
        with Session(engine) as db:
            job = db.get(Job, job_id)
            if job:
                job.status = JobStatus.FAILED
                job.current_agent = None
                job.error_message = str(exc)
                job.updated_at = datetime.now(timezone.utc)
                db.add(job)
                db.commit()