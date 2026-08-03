import os
from datetime import datetime, timezone
from typing import Optional, Generator
from sqlmodel import SQLModel, Field, create_engine, Session
from sqlalchemy import Column, Enum as SAEnum

from src.api.schemas import JobStatus

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./awis.db")

is_sqlite = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


class Job(SQLModel, table=True):
    """
    Persistent job storage model.
    Explicit SAEnum column mapping guarantees round-trip Enum instance restoration.
    """
    __tablename__ = "jobs"

    job_id: str = Field(primary_key=True, index=True)
    user_id: str = Field(index=True, nullable=False)
    
    # Explicit SAEnum column fix to guarantee round-trip Enum casting
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
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session