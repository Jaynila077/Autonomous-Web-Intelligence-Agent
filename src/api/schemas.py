# src/api/schemas.py
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class JobStatus(str, Enum):
    """Lifecycle stages of an AWIA background research job."""
    QUEUED = "QUEUED"
    PLANNING = "PLANNING"
    RESEARCHING = "RESEARCHING"
    VERIFYING = "VERIFYING"
    REPORTING = "REPORTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class QuerySubmitRequest(BaseModel):
    """Payload submitted by the frontend chatbot UI to start a research job."""
    query: str = Field(
        ..., 
        description="The target OSINT research query.",
        min_length=5,
        example="Latest engineering challenges with vector databases"
    )
    max_retries: Optional[int] = Field(
        default=2, 
        description="Maximum retry loops if verification falls below threshold."
    )

class JobStatusResponse(BaseModel):
    """Live status payload returned via API queries or SSE streaming."""
    job_id: str
    user_id: str
    status: JobStatus
    current_agent: Optional[str] = None
    report_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class JobSubmitResponse(BaseModel):
    """Immediate response returned when a query is successfully enqueued."""
    job_id: str
    user_id: str
    status: JobStatus = JobStatus.QUEUED
    status_stream_url: str
    report_download_url: str