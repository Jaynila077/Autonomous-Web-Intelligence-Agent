"""
Internal-only data types for the verifier package.

Everything that's part of the shared pipeline state (ExtractedContent,
VerifiedClaim, AgentState) lives in the project-root schema.py and is
imported from there -- NOT redefined here.

AtomicClaim is intentionally NOT in schema.py: it's a transient value that
only exists between claim_extractor.py and critic.py inside this agent. It
never gets attached to AgentState, so it doesn't need to be a shared type.
"""

from dataclasses import dataclass


@dataclass
class AtomicClaim:
    text: str
    source_url: str
