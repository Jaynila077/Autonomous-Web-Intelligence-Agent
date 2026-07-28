import io
import requests
import xml.etree.ElementTree as ET
from langchain_core.tools import tool
from typing import List, Dict, Any

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
