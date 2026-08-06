# src/tools/email_sender.py
import os
import uuid
import smtplib
import html
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from dotenv import load_dotenv

load_dotenv(override=True)


def send_report_email(to_email: str, subject: str, pdf_path: str, query: str) -> str:
    """
    Sends the generated OSINT PDF report via Gmail SMTP using SSL (port 465).
    """
    gmail_address = os.getenv("GMAIL_ADDRESS")
    gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_address:
        raise RuntimeError("Missing required environment variable: GMAIL_ADDRESS")
    if not gmail_app_password:
        raise RuntimeError("Missing required environment variable: GMAIL_APP_PASSWORD")

    try:
        # Create MIME container
        msg = MIMEMultipart()
        msg["From"] = gmail_address
        msg["To"] = to_email
        msg["Subject"] = subject

        # HTML Body content matching original specs
        html_content = (
            f"<p>Hello,</p>"
            f"<p>Your report for the query: <strong>{html.escape(query)}</strong> is ready.</p>"
            f"<p>Please find the full research report attached as a PDF.</p>"
        )
        msg.attach(MIMEText(html_content, "html"))

        # Attach PDF
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF report not found at path: {pdf_path}")

        with open(pdf_path, "rb") as pdf_file:
            pdf_bytes = pdf_file.read()

        filename = os.path.basename(pdf_path)
        attachment = MIMEApplication(pdf_bytes, Name=filename)
        attachment["Content-Disposition"] = f'attachment; filename="{filename}"'
        msg.attach(attachment)

        # Generate a unique identifier for tracking/logging (mimicking Resend's return ID)
        message_id = f"gmail_smtp_{uuid.uuid4().hex}"
        msg["Message-ID"] = f"<{message_id}@local.awt>"

        # Connect to Gmail SMTP server using SSL on port 465
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, gmail_app_password)
            server.send_message(msg)

        return message_id

    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(f"Failed to send report email: {e}") from e