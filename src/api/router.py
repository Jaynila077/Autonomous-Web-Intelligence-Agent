# src/api/router.py
import uuid
import os
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, BackgroundTasks, HTTPException, Header, status
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse

from src.api.schemas import (
    QuerySubmitRequest,
    JobSubmitResponse,
    JobStatusResponse,
    JobStatus,
)
from src.api.worker import execute_agent_pipeline, job_state_store

router = APIRouter(prefix="/api/v1/queries", tags=["Queries"])


def get_current_user_id(authorization: str = Header(default="usr_demo")) -> str:
    """
    Dependency helper to extract user identity. 
    Replace or extend with full JWT decoding when auth is connected.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    # Simple extraction for demo/testing (e.g. 'Bearer usr_102' -> 'usr_102')
    return authorization.replace("Bearer ", "").strip()


@router.post("/", response_model=JobSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_query(
    payload: QuerySubmitRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Header(default="usr_demo"),
):
    """
    Submits a research query and enqueues the AWIS DeepAgent pipeline.
    Returns immediately with SSE and report download URLs.
    """
    job_id = f"job_{uuid.uuid4().hex[:8]}"

    # Initialize job in state store
    job_state_store[job_id] = {
        "job_id": job_id,
        "user_id": user_id,
        "status": JobStatus.QUEUED,
        "current_agent": None,
        "report_url": None,
        "error_message": None,
    }

    # Dispatch pipeline execution off the main HTTP thread
    background_tasks.add_task(
        execute_agent_pipeline,
        job_id=job_id,
        user_id=user_id,
        query=payload.query,
    )

    return JobSubmitResponse(
        job_id=job_id,
        user_id=user_id,
        status=JobStatus.QUEUED,
        status_stream_url=f"/api/v1/queries/{job_id}/stream",
        report_download_url=f"/api/v1/queries/{job_id}/report",
    )


@router.get("/{job_id}/stream")
async def stream_job_status(job_id: str):
    """
    Server-Sent Events (SSE) endpoint to stream real-time agent execution status.
    """
    if job_id not in job_state_store:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    async def status_event_generator() -> AsyncGenerator[dict, None]:
        last_status = None
        while True:
            current_state = job_state_store.get(job_id)
            if not current_state:
                break

            current_status = current_state.get("status")

            if current_status != last_status:
                yield {
                    "event": "job_status",
                    "data": JobStatusResponse(
                        job_id=current_state["job_id"],
                        user_id=current_state["user_id"],
                        status=current_state["status"],
                        current_agent=current_state.get("current_agent"),
                        report_url=current_state.get("report_url"),
                        error_message=current_state.get("error_message"),
                        created_at=current_state.get("created_at"),
                        updated_at=current_state.get("updated_at"),
                    ).model_dump_json(),
                }
                last_status = current_status

            if current_status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                break

            await asyncio.sleep(1.0)  

    return EventSourceResponse(status_event_generator())


@router.get("/{job_id}/report")
async def get_report_file(job_id: str):
    """
    Downloads or views the final markdown report from the user's isolated workspace.
    """
    job_state = job_state_store.get(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job_state.get("status") != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report not ready. Current job status: {job_state.get('status')}",
        )

    report_path = job_state.get("report_path")
    if not report_path or not os.path.exists(report_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file missing from workspace.",
        )

    return FileResponse(
        path=report_path,
        media_type="text/markdown",
        filename=f"report_{job_id}.md",
    )