import pdfplumber
import requests
import io
import os
import trafilatura
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from langchain_core.tools import tool
from typing import Dict, Any


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


@tool
def extract_article_text(url: str) -> Dict[str, Any]:
    """
    Extracts the main body text (e.g., blog posts, news articles, documentation) 
    from a specific webpage URL and converts it into clean Markdown.
    
    Use this tool AFTER a search tool (like DuckDuckGo dorks or Exa) has identified 
    a highly relevant URL. This tool strips away HTML clutter, sidebars, navigation, 
    and user comments to provide pure semantic text for the LLM to analyze.
    
    Args:
        url (str): The direct hyperlink (URL) of the webpage to extract content from.
        
    Returns:
        Dict[str, Any]: A dictionary containing the extracted data:
            - url (str): The original URL that was parsed.
            - content (str): The extracted main body text formatted as clean Markdown.
            
        If the extraction fails, the site blocks the scraper, or the main body cannot 
        be found, returns a dictionary with an 'error' key detailing the issue.
    """
    try:
        # Fetch the raw HTML
        downloaded_html = trafilatura.fetch_url(url)
        
        if not downloaded_html:
            return {"error": f"Failed to download the page at {url}. Anti-bot protection might be active."}

        # Run extraction heuristics
        clean_text = trafilatura.extract(
            downloaded_html, 
            output_format="markdown",
            include_comments=False,  # Exclude user comments to maintain data quality
            include_links=True       # Keep inline links for context
        )
        
        if not clean_text:
            return {"error": f"Extraction failed for {url}. Trafilatura could not identify a main text body."}
            
        return {
            "url": url,
            "content": clean_text
        }
        
    except Exception as e:
        return {"error": f"An unexpected error occurred during Trafilatura extraction: {str(e)}"}


@tool
def extract_youtube_transcript(video_id: str) -> Dict[str, Any]:
    """
    Extracts and flattens the full spoken subtitles/transcript of a YouTube video.
    
    Use this tool AFTER searching for a video to 'watch' it. By reading the extracted 
    transcript, the LLM can comprehend hours of video content in seconds. 
    
    Args:
        video_id (str): The unique 11-character YouTube identifier (e.g., 'dQw4w9WgXcQ').
        
    Returns:
        Dict[str, Any]: A dictionary containing the extracted transcript data:
            - video_id (str): The ID of the processed video.
            - transcript (str): The full, concatenated spoken text of the video.
            
        If the video has disabled subtitles, requires a login, or an error occurs, 
        returns a dictionary with an 'error' key detailing the issue.
    """
    try:
        # Fetch the transcript (defaults to English, can be extended for i18n)
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Flatten the list of timestamped dictionaries into a single readable string
        formatter = TextFormatter()
        clean_text = formatter.format_transcript(transcript_list)
        
        # Replace heavy newlines to optimize token usage for the LLM context window
        clean_text = clean_text.replace('\n', ' ').strip()
        
        return {
            "video_id": video_id,
            "transcript": clean_text
        }
        
    except Exception as e:
        return {"error": f"Failed to extract transcript for Video ID {video_id}. The creator may have disabled subtitles. Details: {str(e)}"}


@tool
def extract_github_readme(full_name: str, char_limit: int = 3000) -> str:
    """
    Fetches a GitHub repository's README and converts it to plain text.
    Use this tool AFTER search_github_repos, passing the 'full_name' (owner/repo)
    of a specific repo you want to read the documentation for. Falls back to a
    "no README found" message if the repo has none.

    Args:
        full_name: The repository in 'owner/repo' form, as returned by search_github_repos.
        char_limit: Maximum number of characters to return (default is 3000).

    Returns:
        The README content converted to plain text, truncated to char_limit.
    """
    api_url = f"https://api.github.com/repos/{full_name}/readme"
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.get(api_url, headers=headers, timeout=DEFAULT_TIMEOUT)

        if response.status_code == 404:
            return "No README found for this repository."

        if response.status_code != 200:
            return f"Error: Failed to fetch README. HTTP Status Code {response.status_code}"

        data = response.json()
        content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
        return _markdown_to_text(content)[:char_limit]

    except Exception as e:
        return f"Error extracting GitHub README: {str(e)}"


@tool
def extract_lemmy_post(post_id: str, instance: str = "lemmy.world", char_limit: int = 3000) -> str:
    """
    Fetches a Lemmy post's full body plus its top comments from the source instance.
    Use this tool AFTER search_lemmy, passing the 'post_id' of a specific post you
    want to read in full, including discussion (not just the ~300-char preview
    search_lemmy returns).

    Args:
        post_id: The numeric Lemmy post id, as returned by search_lemmy.
        instance: The Lemmy instance host the post lives on (default is 'lemmy.world'),
            should match the 'instance' used in the original search_lemmy call.
        char_limit: Maximum number of characters to return (default is 3000).

    Returns:
        The post body followed by top comments, separated by '---', as plain
        text truncated to char_limit.
    """
    headers = {"User-Agent": "AWIS-OSINT-Agent/2.0 (research use)"}

    try:
        post_resp = requests.get(
            f"https://{instance}/api/v3/post",
            params={"id": post_id}, headers=headers, timeout=DEFAULT_TIMEOUT,
        )
        post_body = ""
        if post_resp.status_code == 200:
            post_body = post_resp.json().get("post_view", {}).get("post", {}).get("body", "") or ""

        parts = [post_body] if post_body else []

        comments_resp = requests.get(
            f"https://{instance}/api/v3/comment/list",
            params={"post_id": post_id, "sort": "Top", "limit": 20},
            headers=headers, timeout=DEFAULT_TIMEOUT,
        )
        if comments_resp.status_code == 200:
            for item in comments_resp.json().get("comments", []):
                body = item.get("comment", {}).get("content", "")
                if body:
                    parts.append(body)

        if not parts:
            return "No post body or comments found for this post_id."

        return "\n---\n".join(parts)[:char_limit]

    except Exception as e:
        return f"Error extracting Lemmy post: {str(e)}"
