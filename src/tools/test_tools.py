import sys
import os
from dotenv import load_dotenv

load_dotenv(override=True)

from src.tools.registry import AWIS_TOOL_REGISTRY


def test_all_tools():
    print("=" * 60)
    print("       AWIS Tool Diagnostics & Health Verification            ")
    print("=" * 60)

    passed = 0
    failed = 0
    results = []

    test_queries = {
        "search_arxiv": {"query": "Deep learning", "max_results": 1},
        "search_arxiv_papers": {"query": "Deep learning", "max_results": 1},
        "search_clinical_trials": {"search_term": "Cancer", "max_results": 1},
        "fetch_wiki_data": {"query": "Artificial intelligence"},
        "search_web_news": {"query": "AI news"},
        "search_tavily": {"query": "Python programming"},
        "search_exa_semantic": {"semantic_query": "Deep learning models"},
        "find_working_searxng": {},
        "search_site_content": {"domain": "github.com", "query": "deepagents"},
        "find_site_feeds": {"domain": "techcrunch.com"},
        "search_github_repos": {"query": "deepagents", "max_results": 1},
        "search_stackexchange": {"query": "python error", "max_results": 1},
        "search_youtube_transcripts": {"query": "AI lecture", "max_results": 1},
        "search_youtube_transcripts_no_key": {"query": "AI lecture"},
        "search_mastodon": {"query": "AI", "max_results": 1},
        "search_lemmy": {"query": "AI"},
        "extract_pdf_with_pdfplumber": {"pdf_url": "https://arxiv.org/pdf/1706.03762.pdf"},
        "save_intelligence_report": {"report_content": "# Diagnostic Test Report\nVerified tool health.", "query_title": "Deep Agents"},
    }

    for tool in AWIS_TOOL_REGISTRY:
        tool_name = tool.name
        print(f"\n[TEST] Testing tool: [{tool_name}] ...", end=" ")

        args = test_queries.get(tool_name, {})
        try:
            res = tool.invoke(args)
            res_str = str(res)
            if res_str and not res_str.startswith("Error:"):
                print("[OK] PASSED")
                passed += 1
                results.append((tool_name, "PASSED", f"{len(res_str)} chars returned"))
            else:
                print("[WARN] WARNING")
                failed += 1
                results.append((tool_name, "WARNING", res_str[:80]))
        except Exception as e:
            print(f"[FAIL] FAILED ({type(e).__name__})")
            failed += 1
            results.append((tool_name, "FAILED", str(e)[:80]))

    print("\n" + "=" * 60)
    print(f"Diagnostics Complete: {passed} PASSED | {failed} ISSUES/WARNINGS")
    print("=" * 60)
    for name, status, info in results:
        symbol = "[OK]" if status == "PASSED" else ("[WARN]" if status == "WARNING" else "[FAIL]")
        print(f"  {symbol} {name:<28} : {status:<8} ({info})")


if __name__ == "__main__":
    test_all_tools()
