from langchain_core.tools import tool
import pdfplumber
import requests
import io

#example 
@tool
def extract_pdf_with_pdfplumber(pdf_url: str, max_pages: int = 10) -> str:
    """
    Downloads a PDF document from a URL into memory and extracts clean raw text page-by-page.
    Use this tool ONLY AFTER obtaining a direct PDF URL (e.g. from search_arxiv) to read the paper in detail.
    
    Args:
        pdf_url: The direct HTTP/HTTPS link to the PDF file.
        max_pages: Maximum number of initial pages to extract (default is 10 to avoid token bloat).
        
    Returns:
        Full extracted text formatted in Markdown with page breaks.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        print(f"Downloading PDF from: {pdf_url}...")
        response = requests.get(pdf_url, headers=headers, timeout=20)
        
        if response.status_code != 200:
            return f"Error: Failed to download PDF. HTTP Status Code {response.status_code}"

        # Stream directly into memory stream (BytesIO) without writing to disk
        pdf_file = io.BytesIO(response.content)
        
        full_text = []
        with pdfplumber.open(pdf_file) as pdf:
            total_pages = len(pdf.pages)
            pages_to_read = min(total_pages, max_pages)
            
            full_text.append(f"# PDF Extraction Report\n**Source URL:** {pdf_url}\n**Total Pages:** {total_pages} (Reading top {pages_to_read})\n\n---\n")
            
            for page_num in range(pages_to_read):
                page = pdf.pages[page_num]
                text = page.extract_text()
                if text:
                    full_text.append(f"### Page {page_num + 1}\n{text.strip()}\n")
                else:
                    full_text.append(f"### Page {page_num + 1}\n[No extractable text found]\n")

        extracted_markdown = "\n".join(full_text)
        
        # Sanity length check
        if len(extracted_markdown.strip()) < 150:
            return f"Warning: Extracted content is insufficient (<150 characters). PDF may be scanned/image-based."

        return extracted_markdown

    except Exception as e:
        return f"Error extracting PDF with pdfplumber: {str(e)}"
