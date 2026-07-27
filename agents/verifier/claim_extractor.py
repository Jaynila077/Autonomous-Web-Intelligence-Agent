"""
Step 2 of the verification engine: Atomic Claim Extraction.

Takes one ExtractedContent item and asks an LLM to break its raw markdown
into small, independently-checkable factual statements.
"""

from typing import List

from schemas.state import ExtractedContent

from .llm_client import LLMClient
from .models import AtomicClaim

SYSTEM_PROMPT = """You extract atomic factual claims from source documents.

Rules:
- Break the text into the smallest independently-checkable factual statements
  (dates, metrics, prices, statuses, product specs, named entities + attribute).
- Do NOT include opinions, marketing language, or claims that can't be
  fact-checked against the source itself.
- Do NOT merge multiple facts into one claim.
- Output ONLY a list of claims, one per line, each starting with "- ".
- Do not add commentary before or after the list."""

USER_PROMPT_TEMPLATE = """DOCUMENT:
{markdown}"""


def extract_atomic_claims(llm: LLMClient, content: ExtractedContent) -> List[AtomicClaim]:
    """Run the extraction LLM call and parse its bullet-list output."""
    user_prompt = USER_PROMPT_TEMPLATE.format(markdown=content.content_markdown)
    raw_output = llm.complete(SYSTEM_PROMPT, user_prompt)

    claims: List[AtomicClaim] = []
    for line in raw_output.splitlines():
        line = line.strip().lstrip("-").strip()
        if line:
            claims.append(AtomicClaim(text=line, source_url=content.url))
    return claims
