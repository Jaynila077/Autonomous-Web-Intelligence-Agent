import os
import base64
import resend

import html

from dotenv import load_dotenv
load_dotenv(override=True)

# Guarded setup at module level; will not crash if missing on import
resend.api_key = os.getenv("RESEND_API_KEY")

def send_report_email(to_email: str, subject: str, pdf_path: str, query: str) -> str:
    """
    Sends an email with a PDF file attached via Resend.
    Reads RESEND_API_KEY and EMAIL_FROM from environment variables.
    Reads the PDF at pdf_path as bytes, base64-encodes it, and attaches it.
    """
    api_key = os.getenv("RESEND_API_KEY")
    email_from = os.getenv("EMAIL_FROM")

    if not api_key:
        raise RuntimeError("Missing required environment variable: RESEND_API_KEY")
    if not email_from:
        raise RuntimeError("Missing required environment variable: EMAIL_FROM")

    # Ensure api_key is set correctly if it was loaded after import
    resend.api_key = api_key

    try:
        with open(pdf_path, "rb") as pdf_file:
            pdf_bytes = pdf_file.read()

        encoded_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
        filename = os.path.basename(pdf_path)

        html_content = (
            f"<p>Hello,</p>"
            f"<p>Your report for the query: <strong>{html.escape(query)}</strong> is ready.</p>"
            f"<p>Please find the full research report attached as a PDF.</p>"
        )

        params = {
            "from": email_from,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
            "attachments": [
                {
                    "filename": filename,
                    "content": encoded_pdf
                }
            ]
        }

        response = resend.Emails.send(params)
        return response["id"]

    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(f"Failed to send report email: {e}") from e