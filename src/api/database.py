import os
from datetime import datetime, timezone
from typing import Optional, Generator
from sqlmodel import SQLModel, Field, create_engine, Session
from src.api.schemas import JobStatus

# Configurable database URL via ENV variable (default to SQLite)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./awis.db")

# Standard connection engine (SQLite specific check for multi-threading)
is_sqlite = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


class Job(SQLModel, table=True):
    """
    Persistent job storage model. Designed to seamlessly link with a
    future `users` table via foreign key once Phase 3 arrives.
    """
    __tablename__ = "jobs"

    job_id: str = Field(primary_key=True, index=True)
    user_id: str = Field(index=True, nullable=False)  # Plain string index ready for Phase 3 FK
    status: JobStatus = Field(default=JobStatus.QUEUED, nullable=False)
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
    """FastAPI Dependency for database sessions."""
    with Session(engine) as session:
        yield session