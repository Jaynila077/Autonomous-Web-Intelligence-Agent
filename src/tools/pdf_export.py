"""
Utility module for converting Markdown research reports into styled PDF files.

Uses `markdown` for Markdown-to-HTML conversion and `xhtml2pdf` for PDF rendering.
"""

import os
from pathlib import Path
import markdown
from xhtml2pdf import pisa


def export_report_to_pdf(markdown_content: str, output_path: str) -> str:
    """Converts a Markdown report string into a PDF file at output_path.

    Args:
        markdown_content: The raw Markdown string to convert.
        output_path: The file path (relative or absolute) where the PDF will be saved.

    Returns:
        str: The absolute path of the generated PDF file on success.

    Raises:
        ValueError: If `markdown_content` is empty.
        RuntimeError: If PDF rendering fails during `xhtml2pdf` compilation.
        IOError: If the file or parent directories cannot be created.
    """
    if not markdown_content or not markdown_content.strip():
        raise ValueError("Cannot convert empty or whitespace-only Markdown content.")

    abs_output_path = os.path.abspath(output_path)
    parent_dir = os.path.dirname(abs_output_path)
    
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    # Convert Markdown content to HTML using required extensions
    html_body = markdown.markdown(
        markdown_content,
        extensions=["tables", "fenced_code"]
    )

    # Clean, print-friendly CSS template compatible with xhtml2pdf
    html_document = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        @page {{
            size: letter portrait;
            margin: 0.75in;
        }}
        body {{
            font-family: Helvetica, Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.5;
            color: #2d3748;
        }}
        h1 {{
            font-size: 18pt;
            color: #1a202c;
            border-bottom: 2px solid #3182ce;
            padding-bottom: 4px;
            margin-top: 20px;
            margin-bottom: 12px;
        }}
        h2 {{
            font-size: 13pt;
            color: #2b6cb0;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 3px;
            margin-top: 16px;
            margin-bottom: 8px;
        }}
        h3 {{
            font-size: 11pt;
            color: #2d3748;
            margin-top: 12px;
            margin-bottom: 6px;
        }}
        p {{
            margin-top: 0;
            margin-bottom: 8px;
            text-align: justify;
        }}
        ul, ol {{
            margin-top: 0;
            margin-bottom: 8px;
            padding-left: 18px;
        }}
        li {{
            margin-bottom: 4px;
        }}
        code {{
            font-family: Courier, "Courier New", monospace;
            background-color: #f7fafc;
            color: #c53030;
            font-size: 8.5pt;
            padding: 1px 3px;
        }}
        pre {{
            background-color: #f7fafc;
            border: 1px solid #e2e8f0;
            padding: 8px 10px;
            font-family: Courier, "Courier New", monospace;
            font-size: 8.5pt;
            line-height: 1.3;
            margin-top: 8px;
            margin-bottom: 12px;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        pre code {{
            background-color: transparent;
            color: inherit;
            padding: 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 8px;
            margin-bottom: 12px;
        }}
        th, td {{
            border: 1px solid #cbd5e0;
            padding: 6px 8px;
            text-align: left;
            font-size: 8.5pt;
        }}
        th {{
            background-color: #edf2f7;
            font-weight: bold;
            color: #2d3748;
        }}
        blockquote {{
            border-left: 3px solid #cbd5e0;
            margin: 8px 0;
            padding-left: 10px;
            color: #4a5568;
            font-style: italic;
        }}
        a {{
            color: #3182ce;
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    {html_body}
</body>
</html>
"""

    try:
        with open(abs_output_path, "wb") as output_file:
            pisa_status = pisa.CreatePDF(html_document, dest=output_file)

        if pisa_status.err:
            raise RuntimeError(
                f"PDF rendering failed with error status code {pisa_status.err}."
            )
    except Exception as exc:
        if not isinstance(exc, RuntimeError):
            raise RuntimeError(
                f"Failed to generate PDF file at '{abs_output_path}': {exc}"
            ) from exc
        raise

    return abs_output_path


if __name__ == "__main__":
    sample_report = """# Executive Summary
This report presents an architectural overview of the AWIS research platform.

## Deep Technical Architecture
The system employs **FastAPI** as the backend web API server, paired with **LangChain/deepagents** for multi-step agent workflows.

* **Component A**: Ingestion Engine
* **Component B**: Agent Execution Service
* **Component C**: PDF Export Pipeline

For further detail, consult the AWIS Documentation.
"""
    test_target = "./test_output.pdf"
    generated_path = export_report_to_pdf(sample_report, test_target)
    print(f"PDF successfully exported to: {generated_path}")