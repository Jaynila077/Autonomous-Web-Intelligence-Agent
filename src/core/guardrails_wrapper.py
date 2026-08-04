import os
import sys
import time
import logging
import asyncio
from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass

logger = logging.getLogger("NeMoGuardrailsWrapper")
logger.setLevel(logging.INFO)

# Import custom action handlers
try:
    from config.actions import (
        mask_pii_action,
        detect_jailbreak_action,
        check_off_topic_action,
        check_toxicity_action,
        check_hallucination_action,
    )
except ImportError:
    # Fallback if config is imported from parent path
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    from config.actions import (
        mask_pii_action,
        detect_jailbreak_action,
        check_off_topic_action,
        check_toxicity_action,
        check_hallucination_action,
    )

# Try importing NeMo Guardrails
NEMO_AVAILABLE = False
try:
    from nemoguardrails import LLMRails, RailsConfig
    NEMO_AVAILABLE = True
except ImportError:
    LLMRails = None
    RailsConfig = None


@dataclass
class GuardrailResult:
    status: str  # "allowed", "blocked_input", "blocked_output", "pii_redacted"
    response: str
    sanitized_prompt: str
    blocked_reason: Optional[str] = None
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "response": self.response,
            "sanitized_prompt": self.sanitized_prompt,
            "blocked_reason": self.blocked_reason,
            "execution_time_ms": self.execution_time_ms,
        }


class NeMoGuardrailsService:
    """
    Enterprise-grade Python wrapper around NVIDIA NeMo Guardrails.
    Provides async pre-flight input validation, post-flight output verification, PII redaction,
    and safe fallback responses without breaking existing core LLM application logic.
    """

    DEFAULT_FALLBACK_MESSAGES = {
        "jailbreak": "I am AWIS agent Don't try this with if you have any query you can continue chat ).",
        "off_topic": "I am an Autonomous Web Intelligence agent. I can only assist with web research, data extraction, and technical analysis tasks.",
        "toxic": "I apologize, but the response was flagged by output safety guardrails (Toxic or Unsafe Content).",
        "hallucination": "I apologize, but the response could not be verified against grounded context (Hallucination detected).",
        "system_error": "An unexpected error occurred during security guardrail processing. Executing safe fallback.",
    }

    def __init__(self, config_dir: str = "config"):
        self.config_dir = os.path.abspath(config_dir)
        self.rails = None
        self.nemo_enabled = False
        self._initialize_rails()

    def _initialize_rails(self):
        """Initializes NeMo LLMRails with custom action registration."""
        if not NEMO_AVAILABLE:
            logger.warning(
                "NVIDIA NeMo Guardrails (`nemoguardrails`) package is not installed. "
                "Falling back to built-in high-performance Python security engine."
            )
            return

        try:
            if os.path.exists(self.config_dir):
                config = RailsConfig.from_path(self.config_dir)
                self.rails = LLMRails(config)
                
                # Register custom Python action handlers
                self.rails.register_action(mask_pii_action, name="mask_pii_action")
                self.rails.register_action(detect_jailbreak_action, name="detect_jailbreak_action")
                self.rails.register_action(check_off_topic_action, name="check_off_topic_action")
                self.rails.register_action(check_toxicity_action, name="check_toxicity_action")
                self.rails.register_action(check_hallucination_action, name="check_hallucination_action")
                
                self.nemo_enabled = True
                logger.info(f"NeMo Guardrails successfully initialized from config at: {self.config_dir}")
            else:
                logger.warning(f"Config path '{self.config_dir}' not found. NeMo Guardrails using fallback mode.")
        except Exception as e:
            logger.error(f"Failed to initialize NeMo Guardrails from '{self.config_dir}': {e}")
            self.nemo_enabled = False

    async def check_input_rails(self, prompt: str) -> GuardrailResult:
        """
        Input Security Layer: Checks for Jailbreak, Off-topic content, and redacts PII.
        """
        start_time = time.time()
        
        # 1. Jailbreak Check
        is_jailbreak = await detect_jailbreak_action(user_input=prompt)
        if is_jailbreak:
            return GuardrailResult(
                status="blocked_input",
                response=self.DEFAULT_FALLBACK_MESSAGES["jailbreak"],
                sanitized_prompt=prompt,
                blocked_reason="Jailbreak / Prompt Injection detected",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        # 2. Off-Topic Check
        is_off_topic = await check_off_topic_action(user_input=prompt)
        if is_off_topic:
            return GuardrailResult(
                status="blocked_input",
                response=self.DEFAULT_FALLBACK_MESSAGES["off_topic"],
                sanitized_prompt=prompt,
                blocked_reason="Off-Topic query out of agent domain",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        # 3. PII Redaction
        sanitized_prompt = await mask_pii_action(text=prompt)
        has_pii = (sanitized_prompt != prompt)

        return GuardrailResult(
            status="pii_redacted" if has_pii else "allowed",
            response="",
            sanitized_prompt=sanitized_prompt,
            blocked_reason=None,
            execution_time_ms=(time.time() - start_time) * 1000,
        )

    async def check_output_rails(self, output: str, context: Optional[str] = None) -> GuardrailResult:
        """
        Output Security Layer: Checks for Toxicity, Hallucinations, and masks output PII.
        """
        start_time = time.time()

        # 1. Toxicity Check
        is_toxic = await check_toxicity_action(bot_response=output)
        if is_toxic:
            return GuardrailResult(
                status="blocked_output",
                response=self.DEFAULT_FALLBACK_MESSAGES["toxic"],
                sanitized_prompt="",
                blocked_reason="Toxic / Unsafe output generated",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        # 2. Hallucination Check
        if context:
            is_hallucinated = await check_hallucination_action(bot_response=output, context=context)
            if is_hallucinated:
                return GuardrailResult(
                    status="blocked_output",
                    response=self.DEFAULT_FALLBACK_MESSAGES["hallucination"],
                    sanitized_prompt="",
                    blocked_reason="Response failed ground-truth fact verification",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )

        # 3. Output PII Masking
        sanitized_output = await mask_pii_action(text=output)

        return GuardrailResult(
            status="allowed",
            response=sanitized_output,
            sanitized_prompt="",
            blocked_reason=None,
            execution_time_ms=(time.time() - start_time) * 1000,
        )

    async def generate_safe_response(
        self,
        prompt: str,
        llm_callable: Optional[Callable[[str], Awaitable[str]]] = None,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Wraps an existing LLM or agent call safely without breaking core logic.

        Args:
            prompt: The raw user prompt.
            llm_callable: Async function taking sanitized prompt string and returning raw model response.
            context: Optional grounding context for hallucination checking.

        Returns:
            Dict containing status, final response, sanitized prompt, and timing.
        """
        total_start = time.time()

        # Phase 1: Pre-flight Input Security Check
        input_check = await self.check_input_rails(prompt)
        if input_check.status == "blocked_input":
            return input_check.to_dict()

        sanitized_prompt = input_check.sanitized_prompt

        # Phase 2: NeMo Guardrails or Core Business Logic LLM Execution
        try:
            if self.nemo_enabled and self.rails and not llm_callable:
                # Execute through NeMo LLMRails engine
                nemo_res = await self.rails.generate_async(prompt=sanitized_prompt)
                raw_response = str(nemo_res)
            elif llm_callable:
                # Execute through existing application LLM function
                raw_response = await llm_callable(sanitized_prompt)
            else:
                raw_response = f"[Mock LLM Response for prompt: '{sanitized_prompt}']"
        except Exception as e:
            logger.error(f"Error during core LLM invocation: {e}", exc_info=True)
            return GuardrailResult(
                status="blocked_input",
                response=self.DEFAULT_FALLBACK_MESSAGES["system_error"],
                sanitized_prompt=sanitized_prompt,
                blocked_reason=f"LLM execution error: {str(e)}",
                execution_time_ms=(time.time() - total_start) * 1000,
            ).to_dict()

        # Phase 3: Post-flight Output Security Check
        output_check = await self.check_output_rails(output=raw_response, context=context)
        if output_check.status == "blocked_output":
            return output_check.to_dict()

        total_time = (time.time() - total_start) * 1000
        return GuardrailResult(
            status="allowed",
            response=output_check.response,
            sanitized_prompt=sanitized_prompt,
            blocked_reason=None,
            execution_time_ms=total_time,
        ).to_dict()
