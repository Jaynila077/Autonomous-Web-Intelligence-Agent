"""
VerifierAgent: orchestrates the full 3-step verification engine.

  1. Content Filtering   -> keep only successfully-extracted sources
  2. Atomic Claim Extraction -> LLM breaks each source into checkable claims
  3. Grounding / NLI Audit   -> critic LLM grades each claim against its source

Only VERIFIED claims are written back to state.verified_claims. If too little
survives, a retry flag is set so the orchestrator can re-fetch data.
"""

import logging
from typing import List

from .claim_extractor import extract_atomic_claims
from .critic import CriticParseError, audit_claim, to_verified_claim
from .llm_client import LLMClient
from .models import AgentState, ExtractedContent, VerifiedClaim

logger = logging.getLogger(__name__)


class VerifierAgent:
    def __init__(self, llm: LLMClient, min_verified_claims: int = 1):
        """
        Args:
            llm: LLM client used for both extraction and critic calls.
            min_verified_claims: if fewer than this many claims end up
                VERIFIED, state.retry is set so the orchestrator can loop
                back and fetch more/better sources.
        """
        self._llm = llm
        self._min_verified_claims = min_verified_claims

    def run(self, state: AgentState) -> AgentState:
        successful_sources = self._filter_successful(state.extracted_data)

        if not successful_sources:
            state.retry = True
            state.retry_reason = "No successfully extracted sources to verify."
            return state

        new_verified: List[VerifiedClaim] = []

        for source in successful_sources:
            atomic_claims = extract_atomic_claims(self._llm, source)
            for claim in atomic_claims:
                try:
                    verdict = audit_claim(self._llm, claim, source_chunk=source.raw_markdown)
                except CriticParseError:
                    logger.warning("Skipping claim (critic parse failure): %s", claim.text)
                    continue

                if verdict.verdict == "VERIFIED":
                    new_verified.append(to_verified_claim(verdict))
                else:
                    logger.info("Rejected claim [%s]: %s", verdict.verdict, claim.text)

        state.verified_claims.extend(new_verified)

        if len(new_verified) < self._min_verified_claims:
            state.retry = True
            state.retry_reason = (
                f"Only {len(new_verified)} claim(s) verified "
                f"(minimum required: {self._min_verified_claims})."
            )

        return state

    @staticmethod
    def _filter_successful(extracted_data: List[ExtractedContent]) -> List[ExtractedContent]:
        return [item for item in extracted_data if item.status == "SUCCESS"]
