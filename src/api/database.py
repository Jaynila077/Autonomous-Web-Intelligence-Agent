# src/api/database.py
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Generator
from sqlmodel import SQLModel, Field, create_engine, Session
from sqlalchemy import Column, Enum as SAEnum

from src.api.schemas import JobStatus

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./awis.db")

is_sqlite = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


class User(SQLModel, table=True):
    """
    User account model for authentication.
    `id` is a string UUID (e.g., 'usr_a1b2c3d4'), matching Job.user_id.
    """
    __tablename__ = "users"

    id: str = Field(
        default_factory=lambda: f"usr_{uuid.uuid4().hex[:12]}",
        primary_key=True,
        index=True,
    )
    email: str = Field(unique=True, index=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Job(SQLModel, table=True):
    """
    Persistent job storage model.
    `user_id` matches User.id format.
    """
    __tablename__ = "jobs"

    job_id: str = Field(primary_key=True, index=True)
    user_id: str = Field(index=True, nullable=False)  # Matches User.id string format
    status: JobStatus = Field(
        default=JobStatus.QUEUED,
        sa_column=Column(SAEnum(JobStatus), nullable=False)
    )
    current_agent: Optional[str] = Field(default=None)
    report_path: Optional[str] = Field(default=None)
    report_url: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def init_db():
    """Creates database tables if they do not exist."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session