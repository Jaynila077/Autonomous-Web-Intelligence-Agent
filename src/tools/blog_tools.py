from ddgs import DDGS
import os
from exa_py import Exa
from langchain_core.tools import tool
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()


@tool
def search_domain_with_dork(domain: str, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Searches a specific domain or blog for a topic using DuckDuckGo search dorks (e.g., 'site:domain query').
    
    Use this tool when you need to find specific articles, tutorials, or documentation 
    within a known target website. This tool ONLY acts as a scout to find relevant URLs 
    and short snippets. It does NOT extract the full article content.
    
    Args:
        domain (str): The target website or sub-directory to restrict the search to (e.g., 'scrapfly.io/blog' or 'towardsdatascience.com').
        query (str): The specific topic, keywords, or question to search for on that domain.
        max_results (int, optional): The maximum number of search results to retrieve. Defaults to 3.
        
    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing the search results. Each dictionary contains:
            - title (str): The search engine title of the webpage.
            - url (str): The direct hyperlink (href) to the webpage (to be passed to an extractor tool).
            - snippet (str): A short text preview/body provided by the search engine.
            
        If no results are found, returns an empty list. If a search engine block or error occurs, returns a list containing a single dictionary with an 'error' key.
    """
    dork_query = f"site:{domain} {query}"
    extracted_results = []
    
    try:
        with DDGS() as ddgs:
            # Execute the dork search
            results = list(ddgs.text(dork_query, max_results=max_results))
            
            if not results:
                return []
            
            # Format the output for the agent
            for result in results:
                extracted_results.append({
                    "title": result.get('title', 'No Title'),
                    "url": result.get('href', 'No Link'),
                    "snippet": result.get('body', 'No Snippet')
                })
                
        return extracted_results
        
    except Exception as e:
        return [{"error": f"Search failed. Anti-bot protection might have blocked the request. Details: {str(e)}"}]


@tool
def search_with_exa(query: str, max_results: int = 2) -> List[Dict[str, Any]]:
    """
    Performs a semantic/neural web search using the Exa AI API to find highly relevant 
    articles, blogs, or documentation, and retrieves AI-extracted highlights.
    
    Use this tool when standard keyword searches (like DuckDuckGo) fail or when you 
    have a complex, natural-language request (e.g., "A highly detailed engineering 
    blog post about bypassing Cloudflare"). 
    
    Args:
        query (str): The semantic search prompt or statement describing the desired content.
        max_results (int, optional): The maximum number of links to retrieve. Defaults to 2.
        
    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing the semantic search matches. Each dictionary contains:
            - title (str): The title of the webpage.
            - url (str): The exact URL of the page.
            - highlights (List[str]): A list of key sentences or paragraphs automatically extracted from the page content by Exa.
            
        If no results are found, returns an empty list. If an API error occurs, returns a list containing a single dictionary with an 'error' key.
    """
    # In a production environment, ensure this is set in your .env or system variables
    exa_api_key = os.environ.get("EXA_API_KEY", "")
    
    if not exa_api_key:
        return [{"error": "EXA_API_KEY environment variable is not set."}]
        
    exa = Exa(api_key=exa_api_key)
    extracted_results = []
    
    try:
        response = exa.search(
            query,
            type="auto",
            num_results=max_results,
            contents={"highlights": True}
        )
        
        results = response.results
        
        if not results:
            return []
            
        for article in results:
            cleaned_highlights = []
            if getattr(article, 'highlights', None):
                cleaned_highlights = [h.replace('\n', ' ').strip() for h in article.highlights]
                
            extracted_results.append({
                "title": article.title,
                "url": article.url,
                "highlights": cleaned_highlights
            })
            
        return extracted_results
        
    except Exception as e:
        return [{"error": f"Exa API call failed: {str(e)}"}]