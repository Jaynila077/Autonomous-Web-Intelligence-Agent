# src/api/database.py
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Generator, List
from sqlmodel import SQLModel, Field, Relationship, create_engine, Session
from sqlalchemy import Column, Enum as SAEnum

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://user:password@localhost:5432/awis_db"
)

# Standard Postgres engine creation (no SQLite-specific connect_args)
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(
        default_factory=lambda: f"usr_{uuid.uuid4().hex[:12]}",
        primary_key=True,
        index=True,
    )
    email: str = Field(unique=True, index=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    conversations: List["Conversation"] = Relationship(back_populates="user")


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: str = Field(
        default_factory=lambda: f"conv_{uuid.uuid4().hex[:12]}",
        primary_key=True,
        index=True,
    )
    user_id: str = Field(foreign_key="users.id", index=True, nullable=False)
    title: Optional[str] = Field(default="New Chat")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    user: User = Relationship(back_populates="conversations")
    messages: List["Message"] = Relationship(back_populates="conversation")


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    job_id: str = Field(primary_key=True, index=True)
    user_id: str = Field(foreign_key="users.id", index=True, nullable=False)
    status: str = Field(
        default="QUEUED",
        sa_column=Column(SAEnum(Enum("JobStatus", ["QUEUED", "PLANNING", "RESEARCHING", "VERIFYING", "REPORTING", "COMPLETED", "FAILED"])), nullable=False)
    )
    current_agent: Optional[str] = Field(default=None)
    report_path: Optional[str] = Field(default=None)
    report_url: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    message: Optional["Message"] = Relationship(back_populates="job")


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: str = Field(
        default_factory=lambda: f"msg_{uuid.uuid4().hex[:12]}",
        primary_key=True,
        index=True,
    )
    conversation_id: str = Field(foreign_key="conversations.id", index=True, nullable=False)
    role: MessageRole = Field(
        sa_column=Column(SAEnum(MessageRole), nullable=False)
    )
    content: Optional[str] = Field(default=None)  # Nullable for pending ASSISTANT reports
    job_id: Optional[str] = Field(default=None, foreign_key="jobs.job_id", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    conversation: Conversation = Relationship(back_populates="messages")
    job: Optional[Job] = Relationship(back_populates="message")


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session