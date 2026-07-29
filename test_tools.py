"""
Standalone tool tester -- calls each tool in the registry directly, with no
LLM/agent involved. Run this first to confirm your environment, API keys,
and network access are all working before testing the full agent pipeline
(which costs LLM calls and is slower to debug).

Usage:
    uv run python test_tools.py
"""

import os
import sys
import traceback

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.tools.search_tools import (
    search_arxiv,
    search_stackexchange,
    search_github_repos,
    search_mastodon,
    search_youtube,
    search_lemmy,
)
from src.tools.extractor_tools import (
    extract_pdf_with_pdfplumber,
    extract_github_readme,
    extract_youtube_transcript,
    extract_lemmy_post,
)

QUERY = "vector databases"


def run(label, fn):
    print(f"\n{'='*70}\n{label}\n{'='*70}")
    try:
        result = fn()
        preview = str(result)
        print(preview[:500] + ("..." if len(preview) > 500 else ""))
        return result
    except Exception as e:
        print(f"RAISED (should not happen -- tools should catch their own errors): {e}")
        traceback.print_exc()
        return None


# ---- Search tools ----
run("search_arxiv", lambda: search_arxiv.invoke({"query": QUERY, "max_results": 2}))
run("search_stackexchange", lambda: search_stackexchange.invoke({"query": QUERY, "max_results": 2}))
gh_results = run("search_github_repos", lambda: search_github_repos.invoke({"query": QUERY, "max_results": 2}))
run("search_mastodon", lambda: search_mastodon.invoke({"query": QUERY, "max_results": 2}))
yt_results = run("search_youtube", lambda: search_youtube.invoke({"query": QUERY, "max_results": 2}))
lemmy_results = run("search_lemmy", lambda: search_lemmy.invoke({"query": QUERY, "max_results": 2}))

# ---- Extractor tools (chained off whatever search just found) ----
if gh_results and isinstance(gh_results, list) and "full_name" in gh_results[0]:
    run("extract_github_readme", lambda: extract_github_readme.invoke(
        {"full_name": gh_results[0]["full_name"], "char_limit": 300}))
else:
    print("\nSkipping extract_github_readme -- no repo result to chain from.")

if yt_results and isinstance(yt_results, list) and "video_id" in yt_results[0]:
    run("extract_youtube_transcript", lambda: extract_youtube_transcript.invoke(
        {"video_id": yt_results[0]["video_id"], "char_limit": 300}))
else:
    print("\nSkipping extract_youtube_transcript -- no video result to chain from (check YOUTUBE_API_KEY).")

if lemmy_results and isinstance(lemmy_results, list) and "post_id" in lemmy_results[0]:
    run("extract_lemmy_post", lambda: extract_lemmy_post.invoke(
        {"post_id": lemmy_results[0]["post_id"], "char_limit": 300}))
else:
    print("\nSkipping extract_lemmy_post -- no post result to chain from.")

# PDF extractor needs a real PDF URL -- using a small public one as a smoke test
run("extract_pdf_with_pdfplumber", lambda: extract_pdf_with_pdfplumber.invoke(
    {"pdf_url": "https://arxiv.org/pdf/1706.03762.pdf", "max_pages": 1}))

print("\n" + "=" * 70)
print("Done. Check above for '[{'error':' entries -- those indicate a")
print("missing API key, network issue, or blocked/rate-limited request,")
print("not a code bug (every tool catches its own exceptions).")
print("=" * 70)
