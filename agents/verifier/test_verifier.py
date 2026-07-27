"""
Standalone test script for the Verifier Agent.

Runs the full 3-step pipeline against dummy extracted_data using a mocked
LLM client (no API key / network access required) and prints the resulting
verified claims plus retry state.

Usage:
    python test_verifier.py
"""

from agents.verifier import AgentState, ExtractedContent, VerifierAgent
from agents.verifier.llm_client import MockLLMClient


def build_dummy_state() -> AgentState:
    sources = [
        ExtractedContent(
            url="https://example.com/product-a",
            status="SUCCESS",
            content_markdown=(
                "Product A launched on March 3, 2024. "
                "It costs $49 per month for the base tier. "
                "Over 12000 teams currently use it in production."
            ),
        ),
        ExtractedContent(
            url="https://example.com/product-b",
            status="SUCCESS",
            content_markdown=(
                "Product B is rumored to support 999 languages, which is unknown "
                "and unverified by the vendor. The interface is described as clean."
            ),
        ),
        ExtractedContent(
            url="https://example.com/broken-page",
            status="FAILED",
            content_markdown="",  # scrape failed, should be filtered out entirely
        ),
    ]
    return AgentState(
        query_id="test-query-001",
        original_query="Dummy query for verifier testing",
        extracted_data=sources,
    )


def main() -> None:
    state = build_dummy_state()
    agent = VerifierAgent(llm=MockLLMClient(), min_verified_claims=1)

    result_state = agent.run(state)

    print("=== Verified Claims ===")
    if not result_state.verified_claims:
        print("(none)")
    for vc in result_state.verified_claims:
        print(f"- [{vc.verdict}] ({vc.confidence_score:.2f}) {vc.claim}  <- {vc.source_url}")

    print("\n=== Retry State ===")
    print(f"retry_count: {result_state.retry_count}")


if __name__ == "__main__":
    main()
