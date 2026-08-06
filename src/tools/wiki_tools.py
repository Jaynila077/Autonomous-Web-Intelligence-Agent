import requests
from typing import Dict, Any

def extract_wikipedia_summary(page_title: str) -> Dict[str, Any]:
    """
    Fetches the clean, structured plain text summary of a Wikipedia page using the MediaWiki API.
    """
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "titles": page_title,
        "prop": "extracts|info",
        "inprop": "url",
        "exintro": True,
        "explaintext": True,
        "exsectionformat": "plain",
        "redirects": 1
    }
    headers = {
        "User-Agent": "AutonomousWebIntelligenceApp/1.0 (Contact: admin@example.com) python-requests"
    }
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        if not pages or "-1" in pages:
            return {"error": f"No Wikipedia page found matching the title: '{page_title}'"}
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