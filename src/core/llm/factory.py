import os
import requests
from langchain_openai import ChatOpenAI

from .callbacks import TokenLoggerCallback
from .groq_patch import ToolParsingChatGroq


def _validate_groq_model(model_name: str, api_key: str) -> None:
    try:
        resp = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        resp.raise_for_status()
        live_ids = {m["id"] for m in resp.json().get("data", [])}
    except Exception:
        return
    if model_name not in live_ids:
        print(
            f"\nWARNING: '{model_name}' is not in Groq's current live model list.\n"
            f"Currently available models include:\n"
            f"  {sorted(live_ids)}\n"
            f"Set GROQ_MODEL in .env to one of the above.\n"
        )


def build_production_llm():
    token_logger = TokenLoggerCallback()

    # 1. Primary Option: NVIDIA NIM API (meta/llama-3.1-70b-instruct)
    nvidia_key = os.getenv("NVIDIA_API_KEY")
    if nvidia_key:
        return ChatOpenAI(
            model=os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct"),
            openai_api_key=nvidia_key,
            openai_api_base="https://integrate.api.nvidia.com/v1",
            temperature=0.0,
            max_retries=5,
            parallel_tool_calls=False,
            callbacks=[token_logger]
        )

    # 2. Secondary Option: Groq LPU
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        _validate_groq_model(model_name, groq_key)
        return ToolParsingChatGroq(
            model_name=model_name,
            groq_api_key=groq_key,
            temperature=0.0,
            max_retries=5,
            parallel_tool_calls=False,
            callbacks=[token_logger]
        )

    gh_token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if gh_token:
        return ChatOpenAI(
            model=os.getenv("GITHUB_MODEL", "gpt-4o-mini"),
            openai_api_key=gh_token,
            openai_api_base="https://models.inference.ai.azure.com",
            temperature=0.0,
            max_retries=5,
            parallel_tool_calls=False,
            callbacks=[token_logger]
        )

    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
                google_api_key=gemini_key,
                temperature=0.0,
                max_retries=5,
                callbacks=[token_logger]
            )
        except ImportError:
            pass

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        return ChatOpenAI(
            model=os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-72b-instruct"),
            openai_api_key=openrouter_key,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.0,
            max_retries=5,
            parallel_tool_calls=False,
            callbacks=[token_logger]
        )

    raise ValueError("No valid API key found in environment variables.")