# src/api/schemas.py
from enum import Enum
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


class MessageRole(str, Enum):
    """Roles for conversation message history."""
    USER = "user"
    ASSISTANT = "assistant"


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
        examples=["Latest engineering challenges with vector databases"]
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Append to an existing conversation if supplied, else starts a new conversation."
    )
    max_retries: Optional[int] = Field(
        default=2, 
        description="Maximum retry loops if verification falls below threshold."
    )


class JobSubmitResponse(BaseModel):
    """Immediate response returned when a query is successfully enqueued."""
    job_id: str
    user_id: str
    conversation_id: str
    user_message_id: str
    assistant_message_id: str
    status: JobStatus = JobStatus.QUEUED
    status_stream_url: str
    report_download_url: str


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


class ConversationResponse(BaseModel):
    """Schema for returning conversation thread metadata for sidebar lists."""
    id: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    """Schema for returning individual chat history entries."""
    id: str
    conversation_id: str
    role: MessageRole
    content: Optional[str] = None
    job_id: Optional[str] = None
    created_at: datetime


# Auth Schemas
class UserRegisterRequest(BaseModel):
    email: EmailStr = Field(..., examples=["user@example.com"])
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters long.")


class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., examples=["user@example.com"])
    password: str = Field(...)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


