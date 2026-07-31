import io
import requests
import xml.etree.ElementTree as ET
import random
import os
from tavily import TavilyClient
from langchain_core.tools import tool
from typing import List, Dict, Any, Optional

#example
@tool
def search_arxiv(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Searches arXiv for scientific research, pre-prints, and academic papers.
    Use this tool FIRST when researching deep technical, AI/ML, or scientific topics
    to find paper titles, abstracts, authors, and direct PDF URLs.
    
    Args:
        query: The search topic or technical keywords (e.g. 'large language model hallucinations').
        max_results: Maximum number of papers to retrieve (default is 3).
        
    Returns:
        List of dictionaries containing paper metadata and direct 'pdf_link' URLs.
    """
    url = "http://export.arxiv.org/api/query"
    
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return [{"error": f"Failed to fetch arXiv data: HTTP {response.status_code}"}]

        root = ET.fromstring(response.content)
        namespace = {'atom': 'http://www.w3.org/2005/Atom'}
        extracted_papers = []

        for entry in root.findall('atom:entry', namespace):
            title = entry.find('atom:title', namespace).text.replace('\n', ' ').strip()
            summary = entry.find('atom:summary', namespace).text.replace('\n', ' ').strip()
            published_date = entry.find('atom:published', namespace).text
            paper_url = entry.find('atom:id', namespace).text
            
            authors = [
                author.find('atom:name', namespace).text 
                for author in entry.findall('atom:author', namespace)
            ]
            
            pdf_link = next(
                (link.attrib['href'] for link in entry.findall('atom:link', namespace) if link.attrib.get('title') == 'pdf'),
                None
            )

            # Ensure PDF link uses https and ends properly
            if pdf_link and not pdf_link.endswith('.pdf'):
                pdf_link = pdf_link + '.pdf'

            extracted_papers.append({
                "title": title,
                "authors": ", ".join(authors),
                "published": published_date[:10],
                "summary": summary,
                "url": paper_url,
                "pdf_link": pdf_link
            })
            
        return extracted_papers

    except Exception as e:
        return [{"error": f"Error querying arXiv API: {str(e)}"}]


@tool
def find_working_searx_instances(max_instances: int = 3) -> List[Dict[str, Any]]:
    """
    Dynamically finds, filters, and tests decentralized Searx/SearxNG metasearch instances.
    
    Use this tool when standard search tools are rate-limited or IP-blocked, and you 
    need a list of active, privacy-respecting search engine URLs to route queries through. 
    This tool does NOT perform a specific search query; it acts as a scout to find 
    healthy server infrastructure.
    
    Args:
        max_instances (int, optional): The maximum number of working instances to verify and return. Defaults to 3.
        
    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing healthy, active instances. Each dictionary contains:
            - url (str): The base URL of the verified SearxNG instance (e.g., 'https://searx.be').
            - type (str): The verified response format the instance supports ('json' or 'html').
            
        If the primary searx.space directory is unreachable or an error occurs, returns a list containing a single dictionary with an 'error' key.
    """
    try:
        # Fetch the master list of instances
        r = requests.get('https://searx.space/data/instances.json', timeout=10)
        r.raise_for_status()
        data = r.json()
        instances = data.get('instances', {})
    except Exception as e:
        return [{"error": f"Failed to fetch instance directory from searx.space: {str(e)}"}]
        
    # Filter for candidates with strong uptime
    candidates = []
    for url, info in instances.items():
        if not url.startswith('https://'):
            continue
        uptime_day = info.get('uptime', {}).get('uptimeDay', 0)
        
        # Only consider instances with greater than 90% uptime
        if uptime_day > 90:
            candidates.append(url.rstrip('/'))
            
    # Shuffle to prevent hammering the same top instances repeatedly
    random.shuffle(candidates)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    working_instances = []
    
    for url in candidates:
        if len(working_instances) >= max_instances:
            break
            
        try:
            # Test 1: Check if the instance supports direct JSON API responses
            resp = requests.get(
                f"{url}/search", 
                params={'q': 'test', 'format': 'json'}, 
                headers=headers, 
                timeout=5
            )
            
            if resp.status_code == 200:
                results = resp.json().get('results', [])
                if results:
                    working_instances.append({
                        "url": url,
                        "type": "json"
                    })
                    continue
            
            # Test 2: If JSON is blocked, verify if it permits raw HTML scraping
            resp_html = requests.get(
                f"{url}/search", 
                params={'q': 'test'}, 
                headers=headers, 
                timeout=5
            )
            
            if resp_html.status_code == 200:
                html_text = resp_html.text.lower()
                # Ensure we haven't hit a Cloudflare block or captcha page
                if "not a bot" not in html_text and "cloudflare" not in html_text and "result" in html_text:
                    working_instances.append({
                        "url": url,
                        "type": "html"
                    })
                    
        except Exception:
            # Fail silently and move to the next candidate
            pass
            
    if not working_instances:
        return [{"error": "Failed to find any working SearxNG instances after filtering."}]
        
    return working_instances


def get_tavily_client() -> TavilyClient:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY environment variable is not set.")
    return TavilyClient(api_key=api_key)


@tool
def tavily_basic_search(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Performs a fast, basic web search using Tavily to retrieve top URLs and text snippets.
    
    Use this tool for quick fact-checking, gathering general web links, or broad 
    discovery where speed is prioritized over deep analysis. It does NOT extract 
    full page content or provide an AI-generated summary.
    
    Args:
        query (str): The search query or question (e.g., 'What are the main causes of solar flares?').
        max_results (int, optional): The maximum number of search results to return. Defaults to 3.
        
    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing the search results. Each dictionary contains:
            - title (str): The title of the webpage.
            - url (str): The direct hyperlink to the page.
            - content (str): A short snippet of relevant text from the page.
            - score (float): The relevance score assigned by Tavily.
            
        If an error occurs, returns a list with a single dictionary containing an 'error' key.
    """
    try:
        client = get_tavily_client()
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=max_results
        )
        
        extracted_results = []
        for result in response.get("results", []):
            extracted_results.append({
                "title": result.get("title", "No Title"),
                "url": result.get("url", ""),
                "content": result.get("content", ""),
                "score": result.get("score", 0.0)
            })
            
        return extracted_results
    except Exception as e:
        return [{"error": f"Tavily basic search failed: {str(e)}"}]


@tool
def tavily_advanced_research(query: str, topic: str = "general", include_domains: Optional[List[str]] = None, max_results: int = 3) -> Dict[str, Any]:
    """
    Performs a deep, advanced web search using Tavily to generate an AI-synthesized answer 
    along with highly filtered, authoritative source links.
    
    Use this tool when you need a comprehensive, synthesized answer to a complex question, 
    or when you need to restrict a deep search to specific trusted domains (e.g., 'news' 
    or specific scientific sites).
    
    Args:
        query (str): The complex research query or topic (e.g., 'Latest news on fusion energy milestones').
        topic (str, optional): The category of the search to optimize results. Must be 'general', 'news', or 'finance'. Defaults to 'general'.
        include_domains (List[str], optional): A list of specific domains to restrict the search to (e.g., ['nature.com', 'sciencedaily.com']). Defaults to None.
        max_results (int, optional): The maximum number of source links to retrieve. Defaults to 3.
        
    Returns:
        Dict[str, Any]: A dictionary containing the advanced research output:
            - ai_answer (str): A detailed, AI-generated summary answering the query based on the aggregated search results.
            - sources (List[Dict]): A list of the highly relevant sources used, containing 'title' and 'url'.
            
        If an error occurs, returns a dictionary with an 'error' key.
    """
    try:
        client = get_tavily_client()
        
        params = {
            "query": query,
            "search_depth": "advanced",
            "topic": topic,
            "include_answer": True,
            "max_results": max_results
        }
        
        if include_domains:
            params["include_domains"] = include_domains
            
        response = client.search(**params)
        
        sources = [
            {"title": res.get("title"), "url": res.get("url")} 
            for res in response.get("results", [])
        ]
        
        return {
            "ai_answer": response.get("answer", "No AI summary could be generated."),
            "sources": sources
        }
    except Exception as e:
        return {"error": f"Tavily advanced research failed: {str(e)}"}


@tool
def extract_webpage_with_tavily(url: str, extraction_query: Optional[str] = None) -> Dict[str, Any]:
    """
    Extracts the clean, relevant text content from a specific webpage URL using Tavily's extraction engine.
    
    Use this tool AFTER a search tool has identified a highly relevant URL. This tool 
    bypasses boilerplate HTML, navigation menus, and ads. If an 'extraction_query' is 
    provided, it specifically targets and extracts text highly relevant to that query.
    
    Args:
        url (str): The direct hyperlink (URL) of the webpage to extract content from.
        extraction_query (str, optional): A specific question or topic to guide the extraction, helping to strip away irrelevant sections of massive pages. Defaults to None.
        
    Returns:
        Dict[str, Any]: A dictionary containing the extracted webpage data:
            - url (str): The requested URL.
            - content (str): The clean, extracted text from the page.
            
        If the extraction fails or the site blocks the request, returns a dictionary with an 'error' key.
    """
    try:
        client = get_tavily_client()
        
        params = {
            "urls": [url],
            "extract_depth": "advanced"
        }
        
        # If a query is provided, use it to focus the extraction
        if extraction_query:
            params["query"] = extraction_query
            
        extraction = client.extract(**params)
        results = extraction.get("results", [])
        
        if not results:
            return {"error": f"Failed to extract any content from {url}."}
            
        # Since we only passed one URL, we grab the first result
        item = results[0]
        
        return {
            "url": item.get("url", url),
            "content": item.get("raw_content", "No content extracted.")
        }
    except Exception as e:
        return {"error": f"Tavily webpage extraction failed: {str(e)}"}