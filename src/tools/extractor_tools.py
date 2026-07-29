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


import html
import os
import re


def _markdown_to_text(md_text: str) -> str:
    """Reduce a Markdown document (with possible inline HTML) down to plain prose."""
    text = md_text or ""
    text = re.sub(r"```[a-zA-Z0-9]*\n?", "", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^\)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r"\1", text)
    text = re.sub(r"<script.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
    text = re.sub(r"(?<!\w)(\*|_)(.*?)\1(?!\w)", r"\2", text)
    text = re.sub(r"^\s*([-*_]\s*){3,}$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


#example
@tool
def extract_github_readme(full_name: str, char_limit: int = 3000) -> str:
    """
    Fetches a GitHub repository's README and converts it to plain text.
    Use this tool AFTER search_github_repos, passing the 'full_name' (owner/repo)
    of a specific repo you want to read the documentation for. Falls back to the
    repo's short description if it has no README.

    Args:
        full_name: The repository in 'owner/repo' form, as returned by search_github_repos.
        char_limit: Maximum number of characters to return (default is 3000).

    Returns:
        The README content converted to plain text, truncated to char_limit.
    """
    import base64
    api_url = f"https://api.github.com/repos/{full_name}/readme"
    headers = {"Accept": "application/vnd.github+json"}

    try:
        response = requests.get(api_url, headers=headers, timeout=10)

        if response.status_code == 404:
            return "No README found for this repository."

        if response.status_code != 200:
            return f"Error: Failed to fetch README. HTTP Status Code {response.status_code}"

        data = response.json()
        content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
        return _markdown_to_text(content)[:char_limit]

    except Exception as e:
        return f"Error extracting GitHub README: {str(e)}"


#example
@tool
def extract_youtube_transcript(video_id: str, char_limit: int = 3000) -> str:
    """
    Fetches the full transcript of a YouTube video.
    Use this tool AFTER search_youtube, passing the 'video_id' of a specific video
    you want to read in full rather than just its description. Falls back to a
    "transcript unavailable" message if the video has no transcript (disabled by
    the uploader, or none in a usable language).
    Requires the youtube-transcript-api package to be installed.

    Args:
        video_id: The YouTube video ID, as returned by search_youtube.
        char_limit: Maximum number of characters to return (default is 3000).

    Returns:
        The video transcript as plain text, truncated to char_limit.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import (
            TranscriptsDisabled,
            NoTranscriptFound,
            VideoUnavailable,
        )
    except ImportError:
        return "Error: youtube-transcript-api is not installed."

    try:
        ytt_api = YouTubeTranscriptApi()
        try:
            fetched = ytt_api.fetch(video_id, languages=["en"])
        except NoTranscriptFound:
            transcript_list = ytt_api.list(video_id)
            transcript = next(iter(transcript_list))
            fetched = transcript.fetch()

        text = " ".join(snippet.text for snippet in fetched)
        return text[:char_limit]

    except (TranscriptsDisabled, VideoUnavailable):
        return "Transcript unavailable for this video (disabled by uploader or video unavailable)."
    except Exception as e:
        return f"Error extracting YouTube transcript: {str(e)}"


#example
@tool
def extract_lemmy_post(post_id: str, instance: str = "lemmy.world", char_limit: int = 3000) -> str:
    """
    Fetches a Lemmy post's body plus its top comments from the source instance.
    Use this tool AFTER search_lemmy, passing the 'post_id' of a specific post you
    want to read in full, including discussion (not just the post body).

    Args:
        post_id: The numeric Lemmy post id, as returned by search_lemmy.
        instance: The Lemmy instance host the post lives on (default is 'lemmy.world').
        char_limit: Maximum number of characters to return (default is 3000).

    Returns:
        The post body followed by top comments, separated by '---', as plain
        text truncated to char_limit.
    """
    api_url = f"https://{instance}/api/v3/comment/list"
    params = {"post_id": post_id, "sort": "Top", "limit": 20}
    headers = {"User-Agent": "awis-osint-tool/1.0 (research use)"}

    try:
        post_resp = requests.get(
            f"https://{instance}/api/v3/post",
            params={"id": post_id}, headers=headers, timeout=10,
        )
        post_body = ""
        if post_resp.status_code == 200:
            post_body = post_resp.json().get("post_view", {}).get("post", {}).get("body", "") or ""

        parts = [post_body]
        response = requests.get(api_url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for item in data.get("comments", []):
                body = item.get("comment", {}).get("content", "")
                if body:
                    parts.append(body)

        return "\n---\n".join(parts)[:char_limit]

    except Exception as e:
        return f"Error extracting Lemmy post: {str(e)}"
