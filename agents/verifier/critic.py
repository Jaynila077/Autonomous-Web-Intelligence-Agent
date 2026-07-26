"""
Step 3 of the verification engine: Grounding & NLI Audit.

Sends each atomic claim, alongside the original source chunk, to a critic
LLM and asks it to judge whether the source actually supports the claim.
This is a separate call from extraction on purpose -- the model auditing a
claim never generated it, which reduces "grading your own homework" bias.
"""

import json
from dataclasses import dataclass

from .llm_client import LLMClient
from .models import AtomicClaim, VerifiedClaim, Verdict

SYSTEM_PROMPT = """You are a strict fact-checking critic performing natural
language inference (NLI) grounding.

Given a CLAIM and a SOURCE TEXT, decide whether the source text actually
supports the claim.

Respond with ONLY a single JSON object, no markdown fences, no commentary,
in exactly this shape:
{
  "claim": "<the claim text>",
  "source_url": "<the source url>",
  "verdict": "VERIFIED" | "CONTRADICTED" | "UNSUPPORTED",
  "confidence_score": <float between 0 and 1>
}

Definitions:
- VERIFIED: the source text directly and unambiguously supports the claim.
- CONTRADICTED: the source text directly conflicts with the claim.
- UNSUPPORTED: the source text neither confirms nor denies the claim
  (e.g. the claim isn't mentioned, or is vague/inferred)."""

USER_PROMPT_TEMPLATE = """CLAIM:
{claim}

SOURCE_URL:
{source_url}

SOURCE TEXT:
{source_chunk}"""


class CriticParseError(Exception):
    """Raised when the critic LLM doesn't return valid, well-formed JSON."""


@dataclass
class CriticVerdict:
    claim: str
    source_url: str
    verdict: Verdict
    confidence_score: float


def audit_claim(llm: LLMClient, claim: AtomicClaim, source_chunk: str) -> CriticVerdict:
    """Run the critic LLM call for a single claim and parse its JSON verdict."""
    user_prompt = USER_PROMPT_TEMPLATE.format(
        claim=claim.text,
        source_url=claim.source_url,
        source_chunk=source_chunk,
    )
    raw_output = llm.complete(SYSTEM_PROMPT, user_prompt, json_mode=True)

    try:
        # Defensive: strip accidental code fences if a model adds them anyway.
        cleaned = raw_output.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(cleaned)
        verdict = data["verdict"]
        if verdict not in ("VERIFIED", "CONTRADICTED", "UNSUPPORTED"):
            raise ValueError(f"Unrecognized verdict: {verdict}")
        return CriticVerdict(
            claim=claim.text,
            source_url=claim.source_url,
            verdict=verdict,
            confidence_score=float(data.get("confidence_score", 0.0)),
        )
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        raise CriticParseError(f"Critic returned unparseable output: {raw_output!r}") from e


def to_verified_claim(verdict: CriticVerdict) -> VerifiedClaim:
    return VerifiedClaim(
        claim=verdict.claim,
        source_url=verdict.source_url,
        verdict=verdict.verdict,
        confidence_score=verdict.confidence_score,
    )
