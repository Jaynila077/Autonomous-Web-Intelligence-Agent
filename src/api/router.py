# src/api/router.py
import uuid
import os
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, BackgroundTasks, HTTPException, Header, Depends, status
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse
from sqlmodel import Session, select

from src.api.schemas import (
    QuerySubmitRequest,
    JobSubmitResponse,
    JobStatusResponse,
    JobStatus,
)
from src.api.database import engine, get_session, Job
from src.api.worker import execute_agent_pipeline

router = APIRouter(prefix="/api/v1/queries", tags=["Queries"])


def get_current_user_id(authorization: str = Header(default="usr_demo")) -> str:
    """
    Centralized identity resolution dependency. 
    Acts as an extensible stub until full JWT authentication arrives in Phase 3.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    user_id = authorization.replace("Bearer ", "").strip()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or empty user authorization identity",
        )
    return user_id


@router.post("/", response_model=JobSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_query(
    payload: QuerySubmitRequest,
    background_tasks: BackgroundTasks,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_session),
):
    job_id = f"job_{uuid.uuid4().hex[:8]}"

    new_job = Job(
        job_id=job_id,
        user_id=current_user_id,
        status=JobStatus.QUEUED,
    )
    db.add(new_job)
    db.commit()

    background_tasks.add_task(
        execute_agent_pipeline,
        job_id=job_id,
        user_id=current_user_id,
        query=payload.query,
    )

    return JobSubmitResponse(
        job_id=job_id,
        user_id=current_user_id,
        status=JobStatus.QUEUED,
        status_stream_url=f"/api/v1/queries/{job_id}/stream",
        report_download_url=f"/api/v1/queries/{job_id}/report",
    )


@router.get("/{job_id}/stream")
async def stream_job_status(
    job_id: str,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Streams job status over SSE while enforcing single-tenant access boundaries.
    Uses `engine` directly to avoid session leaks.
    """
    # 1. Initial permission & existence check using engine directly
    with Session(engine) as db:
        job = db.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
        if job.user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not own this research job.",
            )

    async def status_event_generator() -> AsyncGenerator[dict, None]:
        last_status = None
        while True:
            # 2. Polling loop using engine directly (prevents connection pool exhaustion)
            with Session(engine) as db:
                current_job = db.get(Job, job_id)
                if not current_job:
                    break

                current_status = current_job.status

                if current_status != last_status:
                    yield {
                        "event": "job_status",
                        "data": JobStatusResponse(
                            job_id=current_job.job_id,
                            user_id=current_job.user_id,
                            status=current_job.status,
                            current_agent=current_job.current_agent,
                            report_url=current_job.report_url,
                            error_message=current_job.error_message,
                            created_at=current_job.created_at,
                            updated_at=current_job.updated_at,
                        ).model_dump_json(),
                    }
                    last_status = current_status

                if current_status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                    break

            await asyncio.sleep(1.0)  # SSE Poll interval

    return EventSourceResponse(status_event_generator())


@router.get("/{job_id}/report")
async def get_report_file(
    job_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_session),
):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not own this research job.",
        )

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report not ready. Current job status: {job.status}",
        )

    if not job.report_path or not os.path.exists(job.report_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file missing from workspace.",
        )

    return FileResponse(
        path=job.report_path,
        media_type="text/markdown",
        filename=f"report_{job_id}.md",
    )