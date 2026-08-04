# src/api/router.py
import uuid
import os
import asyncio
from typing import AsyncGenerator, Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Header, Depends, Query, Request, status
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse
from sqlmodel import Session, select
from arq.connections import ArqRedis

from src.api.schemas import (
    QuerySubmitRequest,
    JobSubmitResponse,
    JobStatusResponse,
    JobStatus,
    ConversationResponse,
    MessageResponse,
    MessageRole,
)
from src.api.database import engine, get_session, Job, Conversation, Message
from src.api.auth import decode_access_token

router = APIRouter(prefix="/api/v1", tags=["Queries & Conversations"])


def get_current_user_id(
    authorization: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> str:
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.replace("Bearer ", "").strip()
    elif token:
        raw_token = token.strip()

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return decode_access_token(raw_token)


async def get_arq_redis(request: Request) -> ArqRedis:
    redis_pool = getattr(request.app.state, "arq_redis", None)
    if redis_pool is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Task queue connection not initialized. Startup hook failure.",
        )
    return redis_pool


# ============================================================================
# CONVERSATION ENDPOINTS
# ============================================================================

@router.get("/conversations/", response_model=List[ConversationResponse])
async def list_conversations(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_session),
):
    """List all conversations for the authenticated user (Sidebar)."""
    statement = (
        select(Conversation)
        .where(Conversation.user_id == current_user_id)
        .order_by(Conversation.updated_at.desc())
    )
    conversations = db.exec(statement).all()
    return conversations


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_session),
):
    """Retrieve full message history for a specific conversation."""
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    if conv.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    statement = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    messages = db.exec(statement).all()
    return messages


# ============================================================================
# QUERY SUBMISSION & JOB EXECUTION
# ============================================================================

@router.post("/queries/", response_model=JobSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_query(
    payload: QuerySubmitRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_session),
    arq_redis: ArqRedis = Depends(get_arq_redis),
):
    now = datetime.now(timezone.utc)
    conv_id = payload.conversation_id

    # 1. Conversation resolution
    if conv_id:
        conv = db.get(Conversation, conv_id)
        if not conv:
            raise HTTPException(status_code=404, detail=f"Conversation '{conv_id}' not found.")
        if conv.user_id != current_user_id:
            raise HTTPException(status_code=403, detail="Access denied to conversation.")
        conv.updated_at = now
        db.add(conv)
    else:
        # Generate new conversation auto-titled from query snippet
        auto_title = payload.query[:35] + "..." if len(payload.query) > 35 else payload.query
        conv = Conversation(
            user_id=current_user_id,
            title=auto_title,
            created_at=now,
            updated_at=now,
        )
        db.add(conv)
        db.flush()  # Assigns conv.id without ending the transaction
        conv_id = conv.id

    # 2. Create User Message
    user_msg = Message(
        conversation_id=conv_id,
        role=MessageRole.USER,
        content=payload.query,
        created_at=now,
    )
    db.add(user_msg)

    # 3. Create Job
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    new_job = Job(
        job_id=job_id,
        user_id=current_user_id,
        status=JobStatus.QUEUED,
        created_at=now,
        updated_at=now,
    )
    db.add(new_job)

    # 4. Create Assistant Message (linked to Job, content pending)
    assistant_msg = Message(
        conversation_id=conv_id,
        role=MessageRole.ASSISTANT,
        content=None,  # Populated when worker finishes
        job_id=job_id,
        created_at=now,
    )
    db.add(assistant_msg)

    # Single atomic commit for Conversation + User Message + Job + Assistant Message
    db.commit()

    db.refresh(user_msg)
    db.refresh(assistant_msg)

    # 5. Enqueue to arq worker
    await arq_redis.enqueue_job(
        "execute_agent_pipeline",
        job_id=job_id,
        user_id=current_user_id,
        query=payload.query,
        message_id=assistant_msg.id,
        _job_id=job_id,
    )

    return JobSubmitResponse(
        job_id=job_id,
        user_id=current_user_id,
        conversation_id=conv_id,
        user_message_id=user_msg.id,
        assistant_message_id=assistant_msg.id,
        status=JobStatus.QUEUED,
        status_stream_url=f"/api/v1/queries/{job_id}/stream",
        report_download_url=f"/api/v1/queries/{job_id}/report",
    )


@router.get("/queries/{job_id}/stream")
async def stream_job_status(
    job_id: str,
    current_user_id: str = Depends(get_current_user_id),
):
    with Session(engine) as db:
        job = db.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
        if job.user_id != current_user_id:
            raise HTTPException(status_code=403, detail="Access denied.")

    async def status_event_generator() -> AsyncGenerator[dict, None]:
        last_status = None
        while True:
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

            await asyncio.sleep(1.0)

    return EventSourceResponse(status_event_generator())


@router.get("/queries/{job_id}/report")
async def get_report_file(
    job_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_session),
):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail=f"Report not ready. Status: {job.status}")

    if not job.report_path or not os.path.exists(job.report_path):
        raise HTTPException(status_code=404, detail="Report file missing.")

    return FileResponse(
        path=job.report_path,
        media_type="text/markdown",
        filename=f"report_{job_id}.md",
    )