from langchain_core.callbacks import BaseCallbackHandler

class TokenLoggerCallback(BaseCallbackHandler):
    """
    Real-time token usage and live tool execution logger callback (Windows CP1252 safe).
    """
    def on_tool_start(self, serialized, input_str, **kwargs):
        name = serialized.get("name") if isinstance(serialized, dict) else str(serialized)
        try:
            print(f"\n[LIVE TOOL EXECUTION] Executing Tool: '{name}'", flush=True)
            print(f"    Parameters : {input_str}\n", flush=True)
        except Exception:
            pass

    def on_llm_end(self, response, **kwargs):
        for generations in response.generations:
            for gen in generations:
                info = getattr(gen, "generation_info", {}) or {}
                token_usage = info.get("token_usage") or info.get("usage")
                if token_usage:
                    prompt_tok = token_usage.get("prompt_tokens") or token_usage.get("prompt_eval_count") or "N/A"
                    compl_tok = token_usage.get("completion_tokens") or token_usage.get("eval_count") or "N/A"
                    total_tok = token_usage.get("total_tokens") or "N/A"
                    try:
                        print(f"\n[LLM Token Usage Report]", flush=True)
                        print(f"    Prompt Tokens     : {prompt_tok}", flush=True)
                        print(f"    Completion Tokens : {compl_tok}", flush=True)
                        print(f"    Total Tokens      : {total_tok}", flush=True)
                        print(f"    Cost              : $0.00 (100% FREE)\n", flush=True)
                    except Exception:
                        pass