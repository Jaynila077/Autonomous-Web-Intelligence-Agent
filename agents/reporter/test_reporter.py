import os
from pydantic import BaseModel
from typing import List, Optional
from reporter_agent import ReporterAgent

# ==========================================
# MOCKING SCHEMAS (Strictly for standalone testing)
# ==========================================
class VerifiedClaim(BaseModel):
    claim_text: str
    is_verified: bool
    source_url: str
    confidence_score: int

class AgentState(BaseModel):
    original_query: str
    verified_claims: List[VerifiedClaim]
    final_report: Optional[str] = None

# ==========================================
# MOCK DATA INJECTION
# ==========================================
def get_mock_state() -> AgentState:
    return AgentState(
        original_query="What are the recent findings on automated OSINT reconnaissance frameworks?",
        verified_claims=[
            VerifiedClaim(
                claim_text="SpiderFoot is an open-source automation tool that queries over 100 public data sources simultaneously.",
                is_verified=True,
                source_url="https://github.com/smicallef/spiderfoot",
                confidence_score=9
            ),
            VerifiedClaim(
                claim_text="Recon-ng uses a highly modular architecture similar to Metasploit, but focused on OSINT.",
                is_verified=True,
                source_url="https://github.com/lanmaster53/recon-ng",
                confidence_score=9
            ),
            VerifiedClaim(
                claim_text="theHarvester is used to gather emails and subdomains, but its API keys are entirely free forever.",
                is_verified=False, # Discrepancy injected for LLM to catch
                source_url="https://github.com/laramies/theHarvester",
                confidence_score=4 
            )
        ]
    )

# ==========================================
# TEST EXECUTION
# ==========================================
if __name__ == "__main__":
    # Ensure you run `export GROQ_API_KEY="your_key"` before executing this script
    if not os.environ.get("GROQ_API_KEY"):
        print("ERROR: Please set your GROQ_API_KEY environment variable.")
        exit(1)

    print("Initializing mock AgentState...")
    state = get_mock_state()

    print("Initializing ReporterAgent...")
    reporter = ReporterAgent()

    print("Running ReporterAgent (Calling Groq API)...")
    updated_state = reporter.run(state)

    print("\n--- GENERATED REPORT (MARKDOWN) ---\n")
    print(updated_state.final_report)
    print("\n-----------------------------------\n")

    print("Exporting to Markdown and PDF files...")
    # This will generate /output/report.md and /output/report.pdf
    reporter.export_artifacts(updated_state)
    print("Test Complete.")