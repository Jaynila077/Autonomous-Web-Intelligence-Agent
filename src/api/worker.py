# src/api/worker.py
import os
import asyncio
import time
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Session

from src.api.schemas import JobStatus
from src.api.database import engine, Job, Message

from src.tools.pdf_export import export_report_to_pdf
from src.tools.email_sender import send_report_email
from src.api.database import User

from dotenv import load_dotenv
load_dotenv(override=True)

def _sync_pipeline_runner(user_id: str, job_id: str, query: str) -> str:
    """
    Synchronous wrapper executed inside a background thread (via asyncio.to_thread).
    Branches between the mock agent (fast, no API keys needed) and the real
    AWIS pipeline (src.core.pipeline.runner.run_pipeline) based on MOCK_AGENT.
    """
    mock_agent = os.getenv("MOCK_AGENT", "false").lower() in ("true", "1")

    if mock_agent:
        # Fast local mock path — no LLM calls, no guardrails, just enough to
        # exercise the full API/DB/queue lifecycle in tests.
        time.sleep(2)  # simulate work so status transitions are observable
        report_text = (
            f"# Mock Intelligence Brief (Local Echo)\n\n"
            f"**Query:** {query}\n\n"
            f"This report was generated locally without an external LLM API key."
        )
    else:
        # Real production pipeline — job-scoped workspace, guardrails, retries,
        # and Langfuse tracing all happen inside run_pipeline itself.
        from src.core.pipeline.runner import run_pipeline
        report_text = run_pipeline(query, user_id=user_id, job_id=job_id)

    # Write the report to disk at a job-scoped path, exactly like the real
    # pipeline's workspace convention (workspace/users/{user_id}/jobs/{job_id}/),
    # so GET /report can continue serving a real downloadable .md file via
    # FileResponse, regardless of whether the mock or real path ran.
    vfs_path = os.path.abspath(f"./workspace/users/{user_id}/jobs/{job_id}")
    os.makedirs(vfs_path, exist_ok=True)
    report_path = os.path.join(vfs_path, "final_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    return report_text, report_path


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
        # 2. Run agent pipeline (mock or real) on a background thread
        report_text, report_path = await asyncio.to_thread(_sync_pipeline_runner, user_id, job_id, query)

        if not report_text or not report_text.strip():
            raise ValueError("Pipeline returned an empty report.")

        # 3. DB -> COMPLETED & Populate Message Content + Job.report_path
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

        # 4. Exporting to PDF and Sending Email
        with Session(engine) as db:
            user = db.get(User, user_id)

        if not user or not user.email:
            print(f"Skipping PDF export and email: No valid email found for user_id {user_id}.")
        else:
            if report_path.endswith(".md"):
                pdf_path = report_path[:-3] + ".pdf"
            else:
                pdf_path = report_path + ".pdf"

            final_pdf_path = None

            try:
                final_pdf_path = export_report_to_pdf(report_text, pdf_path)
                print(f"Successfully generated PDF at: {final_pdf_path}")
            except Exception as pdf_exc:
                print(f"Non-fatal error during PDF generation: {pdf_exc}")

            if final_pdf_path:
                try:
                    send_report_email(
                        to_email=user.email,
                        subject=f"Your AWIS Report: {query[:60]}",
                        pdf_path=final_pdf_path,
                        query=query
                    )
                    print(f"Successfully sent email to {user.email}")
                except Exception as email_exc:
                    print(f"Non-fatal error during email sending: {email_exc}")

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
