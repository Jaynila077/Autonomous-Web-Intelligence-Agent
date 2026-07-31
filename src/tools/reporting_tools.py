from datetime import datetime
import os
import re
from langchain_core.tools import tool


@tool
def save_intelligence_report(query_title: str, report_content: str) -> str:
    """
    Saves the final synthesized intelligence report to a unique timestamped Markdown file.
    Always call this tool at the END of the research process to persist results.

    Args:
        query_title: Short title or topic of the research.
        report_content: The full markdown report text.

    Returns:
        Confirmation message with exact file paths.
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
        
    return f"Report successfully saved to '{filepath}' and updated '{latest_path}'."