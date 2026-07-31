import requests
from langchain_core.tools import tool
from typing import Dict, Any

@tool
def extract_wikipedia_summary(page_title: str) -> Dict[str, Any]:
    """
    Fetches the clean, structured plain text summary of a Wikipedia page using the MediaWiki API.
    
    Use this tool to ground the LLM in highly accurate, crowd-sourced factual summaries, 
    historical timelines, and general knowledge. It bypasses HTML parsing entirely to 
    deliver pure semantic text.
    
    Args:
        page_title (str): The specific topic or exact title of the Wikipedia page to search for (e.g., 'Quantum computing', 'World War II').
        
    Returns:
        Dict[str, Any]: A dictionary containing the extracted Wikipedia data:
            - title (str): The official, resolved title of the Wikipedia page.
            - url (str): The direct URL to the full Wikipedia article.
            - summary (str): The plain text introduction/summary of the page, stripped of all HTML and wiki formatting.
            
        If the page does not exist or an API error occurs, returns a dictionary with an 'error' key detailing the issue.
    """
    url = "https://en.wikipedia.org/w/api.php"
    
    # Utilizing the exact parameters defined in your R&D repository 
    # to enforce plain text and bypass HTML chaos.
    params = {
        "action": "query",
        "format": "json",
        "titles": page_title,
        "prop": "extracts|info",
        "inprop": "url",
        "exintro": True,          # Limit to the introduction to save LLM context window space
        "explaintext": True,      # Strip HTML tags
        "exsectionformat": "plain",
        "redirects": 1            # Automatically resolve redirects (e.g., 'USA' -> 'United States')
    }

    headers = {
        "User-Agent": "AutonomousWebIntelligenceApp/1.0 (Contact: admin@example.com) python-requests"
    }

    try:
        # Pass the headers into the GET request
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        pages = data.get("query", {}).get("pages", {})
        
        if not pages or "-1" in pages:
            return {"error": f"No Wikipedia page found matching the title: '{page_title}'"}
            
        # The Wikipedia API returns a dictionary with the page ID as the key
        page_id = list(pages.keys())[0]
        page_data = pages[page_id]
        
        return {
            "title": page_data.get("title", "Unknown Title"),
            "url": page_data.get("fullurl", f"https://en.wikipedia.org/wiki/{page_title}"),
            "summary": page_data.get("extract", "No summary text available.")
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"Error fetching data from Wikipedia API: {str(e)}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}