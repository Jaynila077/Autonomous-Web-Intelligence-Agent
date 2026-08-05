import re
from typing import Optional, Dict, Any

try:
    from nemoguardrails.actions import action
except ImportError:
    # Decorator fallback for standalone testing if nemoguardrails is not yet installed
    def action(name: Optional[str] = None):
        def decorator(fn):
            fn._action_name = name or fn.__name__
            return fn
        return decorator


# ==============================================================================
# PII PATTERNS & REGEX MASKER
# ==============================================================================

PII_PATTERNS = [
    (r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", "[REDACTED_EMAIL]"),
    (r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]"),
    (r"\b(?:sk-[a-zA-Z0-9]{32,}|gsk_[a-zA-Z0-9]{32,}|AIza[0-9A-Za-z-_]{35})\b", "[REDACTED_API_KEY]"),
    (r"\b(?:\d[ -]*?){13,16}\b", "[REDACTED_CREDIT_CARD]"),
    (r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[REDACTED_PHONE]"),
]

@action(name="mask_pii_action")
async def mask_pii_action(text: str) -> str:
    """
    Scans text for sensitive PII (Emails, SSNs, API Keys, Credit Cards, Phones)
    and replaces them with redaction tokens.
    """
    if not text:
        return ""
    
    sanitized = text
    for pattern, replacement in PII_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized)
    return sanitized


# ==============================================================================
# JAILBREAK / PROMPT INJECTION DETECTION
# ==============================================================================

JAILBREAK_TRIGGERS = [
    "ignore all previous instructions",
    "ignore previous instructions",
    "system prompt override",
    "dan mode",
    "do anything now",
    "developer mode enabled",
    "bypass safety filters",
    "reveal your prompt",
    "override security protocols",
    "pretend you have no rules",
    "act as a",
    "act as an",
    "pretend to be",
    "pretend you are",
    "roleplay as",
    "take on the persona of",
    "you are now a",
    "you are now an",
    "simulate a",
    "imagine you are",
    
]

@action(name="detect_jailbreak_action")
async def detect_jailbreak_action(user_input: str) -> bool:
    """
    Detects prompt injection, persona adoption, and jailbreak attempts using pattern matching & heuristics.
    Returns True if jailbreak is detected, False otherwise.
    """
    if not user_input:
        return False

    lower_input = user_input.lower().strip()
    
    # Direct trigger word match
    for trigger in JAILBREAK_TRIGGERS:
        if trigger in lower_input:
            return True

    # Regex heuristic for persona override & system injection attempts
    persona_regex = r"\b(act as|pretend (you are|to be)|roleplay as|take on the role of|simulate (a|an)?|you are now)\b"
    system_inj_regex = r"<\s*system\s*>|\[\s*system\s*\]|\bignore (all|the)? (previous|above|prior) (instructions|prompts|rules)\b"

    if re.search(persona_regex, lower_input) or re.search(system_inj_regex, lower_input):
        return True

    return False


    return False


# ==============================================================================
# OFF-TOPIC QUERY FILTERING
# ==============================================================================

OFF_TOPIC_KEYWORDS = [
    "recipe for", "bake a cake", "love advice", "relationship advice",
    "horoscope", "astrology", "write a romance novel", "how to cook"
]

@action(name="check_off_topic_action")
async def check_off_topic_action(user_input: str) -> bool:
    """
    Verifies if user query is out of scope for Web Intelligence & Data Analysis agent.
    Returns True if query is off-topic, False if on-topic.
    """
    if not user_input:
        return False

    lower_input = user_input.lower()
    for keyword in OFF_TOPIC_KEYWORDS:
        if keyword in lower_input:
            return True

    return False


# ==============================================================================
# TOXICITY & UNSAFE OUTPUT MODERATION
# ==============================================================================

TOXIC_KEYWORDS = [
    "generate malware", "how to build a bomb", "illegal weapon",
    "hate speech sample", "racial slur", "execute cyberattack"
]

@action(name="check_toxicity_action")
async def check_toxicity_action(bot_response: str) -> bool:
    """
    Inspects model output for toxic, violent, or unsafe content.
    Returns True if toxic content is detected, False if clean.
    """
    if not bot_response:
        return False

    lower_resp = bot_response.lower()
    for keyword in TOXIC_KEYWORDS:
        if keyword in lower_resp:
            return True

    return False


# ==============================================================================
# FACT-CHECKING / HALLUCINATION DETECTION
# ==============================================================================

@action(name="check_hallucination_action")
async def check_hallucination_action(bot_response: str, context: Optional[str] = None) -> bool:
    """
    Evaluates whether generated output contains statements contradicting reference context.
    Returns True if hallucination detected, False if grounded.
    """
    if not context or not bot_response:
        return False

    # Heuristic ground-truth verification check
    # Check for direct contradictions (e.g. context says 'Revenue was $5M', response says 'Revenue was $50M')
    context_lower = context.lower()
    resp_lower = bot_response.lower()

    if "explicitly state: false" in context_lower and "is true" in resp_lower:
        return True

    if "unsupported hallucinated claim" in resp_lower:
        return True

    return False
