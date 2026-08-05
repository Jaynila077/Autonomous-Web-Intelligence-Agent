import re
import json
import time
import uuid
import logging

from langchain_groq import ChatGroq
from langchain_core.messages import trim_messages, AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

logger = logging.getLogger(__name__)

# 1. Message Trimmer for context token capping (~4 chars per token)
message_trimmer = trim_messages(
    max_tokens=60000,
    strategy="last",
    token_counter="approximate",
    include_system=True,
    start_on=None,
)

class ToolParsingChatGroq(ChatGroq):
    """
    Parses raw function XML text (<function=name(...)}></function>) from Llama models on Groq.
    Catches Groq HTTP 400 failed_generation exceptions and converts them into valid tool calls.
    """
    def _generate(self, messages, **kwargs):
        trimmed_messages = message_trimmer.invoke(messages)
        res = None
        text = ""
        try:
            res = super()._generate(trimmed_messages, **kwargs)
        except Exception as e:
            err_str = str(e)
            if hasattr(e, "body") and isinstance(e.body, dict):
                text = e.body.get("failed_generation", "")
            if not text and "failed_generation" in err_str:
                match_txt = re.search(r"failed_generation'?: '(.*?)'\}", err_str, re.DOTALL)
                if match_txt:
                    text = match_txt.group(1)

            if text and "<function=" in text:
                name_match = re.search(r'<function=([a-zA-Z0-9_]+)', text)
                json_match = re.search(r'(\{.*\})', text, re.DOTALL)
                if name_match:
                    tool_name = name_match.group(1)
                    args = {}
                    if json_match:
                        raw_json = json_match.group(1).split("</function>")[0].strip()
                        try:
                            args = json.loads(raw_json)
                        except Exception as parse_e:
                            logger.warning(f"[GroqPatch] Failed to parse tool args JSON: {parse_e} — defaulting to empty args")
                            args = {}

                    ai_msg = AIMessage(
                        content="",
                        tool_calls=[{
                            "name": tool_name,
                            "args": args,
                            "id": f"call_{uuid.uuid4().hex[:8]}",
                            "type": "tool_call"
                        }]
                    )
                    gen = ChatGeneration(message=ai_msg)
                    return ChatResult(generations=[gen])
            raise e

        for generations in res.generations:
            for gen in generations:
                msg = getattr(gen, "message", None)
                if msg and hasattr(msg, "content") and isinstance(msg.content, str):
                    text_content = msg.content
                    if "<function=" in text_content:
                        name_match = re.search(r'<function=([a-zA-Z0-9_]+)', text_content)
                        if name_match:
                            tool_name = name_match.group(1)
                            json_match = re.search(r'(\{.*\})', text_content, re.DOTALL)
                            args = {}
                            if json_match:
                                raw_json = json_match.group(1).split("</function>")[0].strip()
                                try:
                                    args = json.loads(raw_json)
                                except Exception as parse_e:
                                    logger.warning(f"[GroqPatch] Failed to parse tool args JSON: {parse_e} — defaulting to empty args")
                                    args = {}

                            msg.tool_calls = [{
                                "name": tool_name,
                                "args": args,
                                "id": f"call_{uuid.uuid4().hex[:8]}",
                                "type": "tool_call"
                            }]
                            msg.content = ""
        return res