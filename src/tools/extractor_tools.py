import io
import os
import re
import requests
import pdfplumber
from typing import Dict, Any, List
try:
    import trafilatura
except ImportError:
    trafilatura = None
from datetime import datetime

DEFAULT_TIMEOUT = 15

def extract_pdf_with_pdfplumber(pdf_url: str, max_pages: int = 10) -> str:
    """
    Downloads a PDF document from a URL into memory and extracts clean raw text page-by-page.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(pdf_url, headers=headers, timeout=DEFAULT_TIMEOUT)
        if response.status_code != 200:
            return f"Error: Failed to download PDF. HTTP Status Code {response.status_code}"
        pdf_file = io.BytesIO(response.content)
        full_text = []
        with pdfplumber.open(pdf_file) as pdf:
            total_pages = len(pdf.pages)
            pages_to_read = min(total_pages, max_pages)
            full_text.append(f"# PDF Extraction Report\n**Source URL:** {pdf_url}\n**Total Pages:** {total_pages}\n\n---\n")
            for page_num in range(pages_to_read):
                page = pdf.pages[page_num]
                text = page.extract_text()
                if text:
                    full_text.append(f"### Page {page_num + 1}\n{text.strip()}\n")
                else:
                    full_text.append(f"### Page {page_num + 1}\n[No extractable text found]\n")
        extracted_markdown = "\n".join(full_text)
        if len(extracted_markdown.strip()) < 150:
            return f"Warning: Extracted content is insufficient (<150 characters). PDF may be scanned/image-based."
        return extracted_markdown
    except Exception as e:
        return f"Error extracting PDF with pdfplumber: {str(e)}"

def extract_article_text(url: str) -> Dict[str, Any]:
    """
    Extracts the main body text from a specific webpage URL and converts it into clean Markdown.
    """
    try:
        downloaded_html = trafilatura.fetch_url(url)
        if not downloaded_html:
            return {"error": f"Failed to download the page at {url}. Anti-bot protection might be active."}
        clean_text = trafilatura.extract(
            downloaded_html,
            output_format="markdown",
            include_comments=False,
            include_links=True
        )
        if not clean_text:
            return {"error": f"Extraction failed for {url}. Trafilatura could not identify a main text body."}
        return {
            "url": url,
            "content": clean_text
        }
    except Exception as e:
        return {"error": f"An unexpected error occurred during Trafilatura extraction: {str(e)}"}

def save_intelligence_report(query_title: str, report_content: str) -> str:
    """
    Saves the final synthesized intelligence report to a unique timestamped Markdown file.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r'[^a-zA-Z0-9]+', '_', query_title.strip().lower()).strip('_')[:30]
    filename = f"report_{slug}_{timestamp}.md"
    reports_dir = os.path.abspath("./workspace/reports")
    os.makedirs(reports_dir, exist_ok=True)
    filepath = os.path.join(reports_dir, filename)
    latest_path = os.path.abspath("./workspace/latest_report.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report_content)
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    return f"TERMINATE_SUBAGENT: Report successfully saved to '{filepath}' and updated '{latest_path}'. STOP all tool calls now."