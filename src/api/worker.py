# src/api/worker.py
import os
import asyncio
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Session

from src.core.main import build_awis_agent
from src.api.schemas import JobStatus
from src.api.database import engine, Job, Message


def _sync_pipeline_runner(user_id: str, job_id: str, query: str) -> str:
    agent, vfs_path = build_awis_agent(user_id=user_id, job_id=job_id)
    agent.invoke({"messages": [{"role": "user", "content": query}]})
    return os.path.join(vfs_path, "final_report.md")


async def execute_agent_pipeline(ctx: dict, job_id: str, user_id: str, query: str, message_id: Optional[str] = None):
    now = datetime.now(timezone.utc)

    # 1. DB -> RESEARCHING
    with Session(engine) as db:
        job = db.get(Job, job_id)
        if job:
            job.status = JobStatus.RESEARCHING
            job.current_agent = "Researcher"
            job.updated_at = now
            db.add(job)
            db.commit()

    try:
        # 2. Run agent pipeline on background thread
        report_path = await asyncio.to_thread(_sync_pipeline_runner, user_id, job_id, query)

        if not os.path.exists(report_path):
            raise FileNotFoundError(f"Expected report at {report_path}, but file was not created.")

        with open(report_path, "r", encoding="utf-8") as f:
            report_text = f.read()

        # 3. DB -> COMPLETED & Populate Message Content
        with Session(engine) as db:
            job = db.get(Job, job_id)
            if job:
                job.status = JobStatus.COMPLETED
                job.current_agent = "Reporter"
                job.report_path = report_path
                job.report_url = f"/api/v1/queries/{job_id}/report"
                job.updated_at = datetime.now(timezone.utc)
                db.add(job)

            if message_id:
                msg = db.get(Message, message_id)
                if msg:
                    msg.content = report_text
                    db.add(msg)

            db.commit()

    except Exception as exc:
        with Session(engine) as db:
            job = db.get(Job, job_id)
            if job:
                job.status = JobStatus.FAILED
                job.current_agent = None
                job.error_message = str(exc)
                job.updated_at = datetime.now(timezone.utc)
                db.add(job)

            if message_id:
                msg = db.get(Message, message_id)
                if msg:
                    msg.content = f"Error generating report: {str(exc)}"
                    db.add(msg)

            db.commit()