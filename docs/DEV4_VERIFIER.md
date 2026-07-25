# TASK INSTRUCTIONS: Developer 4 (Verifier Agent / Audit Loop)

## Objective
Build the 3-Step Verification Engine to audit extracted content for facts, eliminate hallucinations, and ground claims against sources.

## Inputs & Outputs
- **Input:** `state.extracted_data` (List[ExtractedContent]) from `AgentState`.
- **Output:** Append structured claims to `state.verified_claims`. Trigger retry flag if data is insufficient.

## Required Responsibilities
1. **Content Filtering:** Filter out items in `extracted_data` where `status != "SUCCESS"`.
2. **Atomic Claim Extraction:** Prompt an LLM to parse raw Markdown and extract individual atomic factual claims (dates, metrics, status, product specs).
3. **Grounding & NLI Audit:** Pass each extracted claim + raw source chunk back to a Critic LLM using JSON mode:
   \`\`\`json
   {
     "claim": "string",
     "source_url": "string",
     "verdict": "VERIFIED | CONTRADICTED | UNSUPPORTED",
     "confidence_score": 0.95
   }
   \`\`\`
4. **State Update:** Append only claims with `verdict == "VERIFIED"` to `state.verified_claims`.

## Code Boundary
You must ONLY write code inside the `/agents/verifier/` directory.

## Mock Test Interface
Provide a standalone test script `test_verifier.py` that accepts dummy `extracted_data` text and outputs verified claims.