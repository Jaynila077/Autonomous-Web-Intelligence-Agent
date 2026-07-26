"""
Thin LLM client abstraction so the verifier logic doesn't care whether it's
talking to a real model or a mock in tests.

Real code should call `AnthropicLLMClient`; `test_verifier.py` uses
`MockLLMClient` so the test runs offline / without an API key.
"""

from abc import ABC, abstractmethod
from typing import Optional


class LLMClient(ABC):
    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        """Return the raw text completion for a single-turn prompt."""
        raise NotImplementedError


class AnthropicLLMClient(LLMClient):
    """Real client, backed by the Anthropic API."""

    def __init__(self, model: str = "claude-sonnet-4-6", api_key: Optional[str] = None):
        import anthropic  # imported lazily so the mock path has no hard dependency

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def complete(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        # json_mode is enforced via prompting (Claude has no dedicated JSON-mode
        # flag) -- the callers below already instruct "respond with JSON only".
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(block.text for block in response.content if block.type == "text")


class MockLLMClient(LLMClient):
    """
    Deterministic fake used by test_verifier.py. Matches on keywords in the
    prompt so the mock test script can exercise extraction + all three
    verdict branches without hitting a real API.
    """

    def complete(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        if "extract" in system_prompt.lower():
            return self._mock_extraction(user_prompt)
        return self._mock_critic(user_prompt)

    def _mock_extraction(self, user_prompt: str) -> str:
        # Pretend-extraction: split on sentences containing a digit (a cheap
        # proxy for "looks like a factual claim") so the mock output changes
        # with the input text instead of being hardcoded.
        import re

        text = user_prompt.split("DOCUMENT:\n", 1)[-1]
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        claims = [s.strip() for s in sentences if any(ch.isdigit() for ch in s)]
        if not claims:
            claims = sentences[:1]
        return "\n".join(f"- {c}" for c in claims if c)

    def _mock_critic(self, user_prompt: str) -> str:
        import json

        claim_lower = user_prompt.lower()
        if "999" in claim_lower or "unicorn" in claim_lower:
            verdict, score = "CONTRADICTED", 0.9
        elif "rumor" in claim_lower or "unknown" in claim_lower:
            verdict, score = "UNSUPPORTED", 0.4
        else:
            verdict, score = "VERIFIED", 0.93
        return json.dumps({
            "claim": "mock",
            "source_url": "mock",
            "verdict": verdict,
            "confidence_score": score,
        })
