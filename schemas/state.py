from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ScoutLink(BaseModel):
    url: str
    title: str
    scope_type: str  # e.g., "OFFICIAL_PR", "NEWS", "COMMUNITY_FORUM"
    snippet: str

class ExtractedContent(BaseModel):
    url: str
    content_markdown: str
    status: str  # "SUCCESS" | "FAILED" | "INSUFFICIENT"
    metadata: Dict[str, Any] = {}

class VerifiedClaim(BaseModel):
    claim: str
    source_url: str
    verdict: str  # "VERIFIED" | "CONTRADICTED" | "UNSUPPORTED"
    confidence_score: float

class AgentState(BaseModel):
    query_id: str
    original_query: str
    plan: List[str] = []
    scouted_links: List[ScoutLink] = []
    extracted_data: List[ExtractedContent] = []
    verified_claims: List[VerifiedClaim] = []
    final_report: Optional[str] = None
    retry_count: int = 0
