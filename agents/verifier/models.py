"""
Shared data models for the Verifier Agent.

In the full system these likely already exist in a central `state.py` /
`schemas.py` module owned by the orchestrator. They're redefined here so this
package is self-contained and independently testable. Swap these imports for
the real shared module once it exists.
"""

from dataclasses import dataclass, field
from typing import List, Literal, Optional


Status = Literal["SUCCESS", "FAILED", "TIMEOUT"]
Verdict = Literal["VERIFIED", "CONTRADICTED", "UNSUPPORTED"]


@dataclass
class ExtractedContent:
    """One scraped/extracted source, produced by an upstream extractor agent."""
    url: str
    raw_markdown: str
    status: Status = "SUCCESS"


@dataclass
class AtomicClaim:
    """A single factual statement pulled out of a source document."""
    text: str
    source_url: str


@dataclass
class VerifiedClaim:
    """The final, audited output that gets appended to AgentState.verified_claims."""
    claim: str
    source_url: str
    verdict: Verdict
    confidence_score: float


@dataclass
class AgentState:
    """
    Minimal stand-in for the shared AgentState object. Only the fields the
    verifier reads/writes are included.
    """
    extracted_data: List[ExtractedContent] = field(default_factory=list)
    verified_claims: List[VerifiedClaim] = field(default_factory=list)
    retry: bool = False
    retry_reason: Optional[str] = None
