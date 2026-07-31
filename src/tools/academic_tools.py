import requests
import xml.etree.ElementTree as ET
from langchain_core.tools import tool
from typing import List, Dict, Any

@tool
def search_arxiv_papers(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Searches the arXiv API for academic papers based on a search query and returns metadata.
    
    Use this tool to find relevant peer-reviewed studies, methodologies, and scientific 
    consensus. This tool ONLY performs the search and metadata extraction. It does NOT 
    read or extract the full text of the PDFs.
    
    Args:
        query (str): The search topic or technical keywords to look up (e.g., 'machine learning').
        max_results (int, optional): The maximum number of research papers to retrieve. Defaults to 3.
        
    Returns:
        List[Dict[str, Any]]: A list of dictionaries, where each dictionary represents a paper and contains:
            - title (str): The title of the paper.
            - authors (str): A comma-separated list of author names.
            - published (str): The publication date in 'YYYY-MM-DD' format.
            - summary (str): The abstract or summary of the paper.
            - url (str): The arXiv abstract page URL.
            - pdf_link (str): The direct URL to download the paper's PDF file (to be passed to a PDF extractor).
            
        If an error occurs, returns a list containing a single dictionary with an 'error' key.
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
            return [{"error": f"Failed to fetch data from arXiv API: HTTP {response.status_code}"}]

        # Parse the XML response
        root = ET.fromstring(response.content)
        
        # arXiv XML uses namespaces
        namespace = {'atom': 'http://www.w3.org/2005/Atom'}
        extracted_papers = []
        
        for entry in root.findall('atom:entry', namespace):
            title = entry.find('atom:title', namespace).text.replace('\n', ' ').strip()
            summary = entry.find('atom:summary', namespace).text.replace('\n', ' ').strip()
            published_date = entry.find('atom:published', namespace).text
            paper_url = entry.find('atom:id', namespace).text
            
            # Extract authors
            authors = [
                author.find('atom:name', namespace).text 
                for author in entry.findall('atom:author', namespace)
            ]
            
            # Extract the direct PDF link
            pdf_link = next(
                (link.attrib['href'] for link in entry.findall('atom:link', namespace) 
                 if link.attrib.get('title') == 'pdf'), 
                None
            )
            
            # Format and append
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