import sys
import json
import traceback
import asyncio

# NOTE: This test suite requires all 5 MCP servers to be running locally.
# Start them first in a separate terminal using:
#     python -m src.mcp_servers.run_all

try:
    from src.tools.registry import AWIS_TOOL_REGISTRY
except RuntimeError as e:
    print(str(e))
    sys.exit(1)

async def main():
    print("=" * 70)
    print("  AWIS MCP Tool Integration Diagnostics  ")
    print("=" * 70)
    print("[INFO] Validating tools via LangChain MCP Adapters...\n")

    test_args = {
        "search_arxiv": {"query": "quantum computing", "max_results": 1},
        "search_arxiv_papers": {"query": "machine learning", "max_results": 1},
        "search_clinical_trials": {"search_term": "mRNA vaccine", "limit": 1},
        "fetch_wiki_data": {"query": "Artificial intelligence"},
        "search_web_news": {"query": "AI news", "max_results": 1},
        "search_tavily": {"query": "fusion energy news", "max_results": 1},
        "search_exa_semantic": {"semantic_query": "deep learning models", "max_links": 1},
        "find_working_searxng": {"max_instances": 1},
        "search_site_content": {"domain": "scrapfly.io", "query": "web scraping", "max_results": 1},
        "find_site_feeds": {"domain": "techcrunch.com"},
        "search_github_repos": {"query": "agentic ai framework", "limit": 1},
        "search_stackexchange": {"query": "python dict KeyError", "max_results": 1},
        "search_youtube_transcripts": {"query": "SpaceX Starship launch", "max_results": 1},
        "search_youtube_transcripts_no_key": {"query": "SpaceX Starship launch", "max_results": 1},
        "search_mastodon": {"query": "AI", "max_results": 1},
        "search_lemmy": {"query": "AI", "max_results": 1},
        "extract_pdf_with_pdfplumber": {"pdf_url": "https://arxiv.org/pdf/1706.03762.pdf", "max_pages": 1},
        "extract_pdf": {"pdf_url": "https://arxiv.org/pdf/1706.03762.pdf", "max_pages": 1},
        "extract_webpage": {"url": "https://en.wikipedia.org/wiki/Web_scraping"},
        "extract_wikipedia_summary": {"page_title": "Quantum computing"},
        "monitor_rss_feed": {"feed_url": "http://feeds.bbci.co.uk/news/technology/rss.xml", "max_articles": 1},
        "save_intelligence_report": {"query_title": "Test", "report_content": "# Test Report\nVerified."}
    }

    passed = 0
    failed_tools = []
    total_tools = len(AWIS_TOOL_REGISTRY)

    if total_tools == 0:
        print("[FAIL] AWIS_TOOL_REGISTRY is empty. MCP Client failed to discover any tools.")
        sys.exit(1)

    for tool in AWIS_TOOL_REGISTRY:
        tool_name = tool.name
        print(f"Testing [{tool_name}]...", end=" ", flush=True)

        args = test_args.get(tool_name, {})
        
        try:
            # LangChain tool invocation over MCP requires async
            result = await tool.ainvoke(args)
            
            # Catch soft errors returned as valid text/json
            res_str = str(result)
            if "error" in res_str.lower() and "exception" in res_str.lower():
                print(f"[FAIL]\n    -> Soft Error Output: {res_str[:150]}...")
                failed_tools.append((tool_name, "Returned soft error inside output."))
            else:
                print(f"[PASS] (Returned {len(res_str)} chars)")
                passed += 1
                
        except Exception as e:
            print("[FAIL]")
            err_msg = str(e).splitlines()[0] if str(e) else type(e).__name__
            print(f"    -> Exception: {err_msg}")
            failed_tools.append((tool_name, err_msg))

    print("\n" + "=" * 70)
    print(f"Diagnostics Complete: {passed}/{total_tools} PASSED")
    print("=" * 70)

    if failed_tools:
        print("\nFailed Tools Summary:")
        for name, err in failed_tools:
            print(f" - {name}: {err}")
        sys.exit(1)
    else:
        print("\nAll tools executed successfully over MCP!")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())