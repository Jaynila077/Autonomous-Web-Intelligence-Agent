# TASK INSTRUCTIONS: Developer 5 (Reporter Agent & Presentation UI)

## Objective
Build the Report Synthesizer and Minimal UI Dashboard to render final intelligence briefs.

## Inputs & Outputs
- **Input:** `state.verified_claims` (List[VerifiedClaim]) and `state.original_query` from `AgentState`.
- **Output:** Generated `state.final_report` (Markdown/PDF) and UI rendering.

## Required Responsibilities
1. **Report Generation:** Prompt an LLM to summarize `verified_claims` into a structured Discrepancy & Intelligence Brief containing:
   - Executive Summary
   - Key Verified Findings
   - Source Citations & URLs (hyperlinked)
   - Confidence Ratings
2. **Formatting:** Export the final report to Markdown and PDF (`ReportLab` / `WeasyPrint` / `markdown2`).
3. **UI / Display:** Build a lightweight Streamlit or Next.js dashboard showing:
   - Input Query field
   - Active execution status
   - Final report with clickable citations

## Code Boundary
You must ONLY write code inside `/agents/reporter/` and `/ui/`.

## Mock Test Interface
Provide a standalone test script `test_reporter.py` that takes a list of dummy `verified_claims` and renders the final report.
