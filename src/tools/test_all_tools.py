import json
from dotenv import load_dotenv

# Import all tools from your repository files
from academic_tools import search_arxiv_papers
from blog_tools import search_domain_with_dork, search_with_exa
from extractor_tools import extract_pdf_with_pdfplumber, extract_article_text
from health_tools import search_clinical_trials
from news_tools import search_news_duckduckgo, monitor_rss_feed
from search_tools import (
    search_arxiv, find_working_searx_instances, 
    tavily_basic_search, tavily_advanced_research, extract_webpage_with_tavily
)
from wiki_tools import extract_wikipedia_summary
from youtube_tools import search_youtube_videos, extract_youtube_transcript

# Load environment variables (.env) for API keys (Exa, Tavily, YouTube)
load_dotenv()

def run_test(tool_name, func, **kwargs):
    """
    Helper function to run a LangChain tool using .invoke(), catch exceptions, and format the output.
    """
    print(f"\n{'='*60}")
    print(f"🛠️  Testing Tool: {tool_name}")
    print(f"{'='*60}")
    try:
        # 🔑 THE FIX: Use .invoke() for LangChain tools and pass arguments as a dictionary
        result = func.invoke(kwargs)
        
        # Many of the tools return a list with an error dictionary if they fail gracefully
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict) and "error" in result[0]:
            print(f"❌ Tool returned a soft error:\n{json.dumps(result, indent=2)}")
        elif isinstance(result, dict) and "error" in result:
            print(f"❌ Tool returned a soft error:\n{json.dumps(result, indent=2)}")
        else:
            print("✅ Tool is working! Sample Output:")
            
            # Format and truncate long outputs for readability
            if isinstance(result, (dict, list)):
                formatted_out = json.dumps(result, indent=2)
            else:
                formatted_out = str(result)
                
            if len(formatted_out) > 1000:
                print(formatted_out[:1000] + "\n... [OUTPUT TRUNCATED FOR READABILITY]")
            else:
                print(formatted_out)
                
    except Exception as e:
        print(f"❌ Hard Exception occurred during execution:\n{str(e)}")

def main():
    # 1. Academic Tools
    run_test("search_arxiv_papers", search_arxiv_papers, query="machine learning", max_results=1)

    # 2. Blog Tools
    run_test("search_domain_with_dork", search_domain_with_dork, domain="scrapfly.io", query="web scraping", max_results=1)
    run_test("search_with_exa", search_with_exa, query="web scraping techniques", max_results=1)

    # 3. Extractor Tools
    # Using the famous "Attention Is All You Need" paper PDF for testing
    run_test("extract_pdf_with_pdfplumber", extract_pdf_with_pdfplumber, pdf_url="https://arxiv.org/pdf/1706.03762.pdf", max_pages=1) 
    run_test("extract_article_text", extract_article_text, url="https://en.wikipedia.org/wiki/Web_scraping")

    # 4. Health Tools
    run_test("search_clinical_trials", search_clinical_trials, query="mRNA vaccine", limit=1)

    # 5. News Tools
    run_test("search_news_duckduckgo", search_news_duckduckgo, query="Artificial Intelligence", max_results=1)
    # Using BBC Technology RSS feed
    run_test("monitor_rss_feed", monitor_rss_feed, feed_url="http://feeds.bbci.co.uk/news/technology/rss.xml", max_articles=1)

    # 6. Search Tools
    run_test("search_arxiv", search_arxiv, query="quantum computing", max_results=1)
    run_test("find_working_searx_instances", find_working_searx_instances, max_instances=1)
    run_test("tavily_basic_search", tavily_basic_search, query="latest fusion energy news", max_results=1)
    run_test("tavily_advanced_research", tavily_advanced_research, query="fusion energy milestones", topic="news", max_results=1)
    run_test("extract_webpage_with_tavily", extract_webpage_with_tavily, url="https://en.wikipedia.org/wiki/Fusion_power")

    # 7. Wiki Tools
    run_test("extract_wikipedia_summary", extract_wikipedia_summary, page_title="Quantum computing")

    # 8. YouTube Tools
    run_test("search_youtube_videos", search_youtube_videos, query="SpaceX Starship launch", max_results=1)
    # Using "Me at the zoo" (the first YouTube video ever) for transcript testing
    run_test("extract_youtube_transcript", extract_youtube_transcript, video_id="jNQXAC9IVRw") 

if __name__ == "__main__":
    main()