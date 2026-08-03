import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from src.tools.cache_manager import cache_result, truncate_tool_output

DEFAULT_TIMEOUT = 10

@cache_result(expire=86400, prefix="academic")
def _fetch_arxiv(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending"
    }
    try:
        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
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
            if pdf_link and not pdf_link.endswith('.pdf'):
                pdf_link = pdf_link + '.pdf'
            extracted_papers.append({
                "title": title,
                "authors": ", ".join(authors),
                "published": published_date[:10],
                "summary": summary,
                "url": paper_url,
                "pdf_link": pdf_link,
                "source_platform": "arXiv"
            })
        return extracted_papers
    except Exception as e:
        return [{"error": f"Error querying arXiv API: {str(e)}"}]

def search_arxiv(query: str, max_results: int = 3) -> str:
    """
    Searches arXiv for scientific research, pre-prints, and academic papers (Cached 24h).
    """
    res = _fetch_arxiv(query=query, max_results=max_results)
    return truncate_tool_output(res, max_chars=1200)

@cache_result(expire=86400, prefix="clinical")
def _fetch_clinical_trials(search_term: str, limit: int = 5) -> List[Dict[str, Any]]:
    url = "https://clinicaltrials.gov/api/v2/studies"
    params = {"query.term": search_term, "pageSize": limit, "format": "json"}
    try:
        response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        return [{"error": f"Error fetching clinical trials: {str(e)}"}]
    extracted_trials = []
    for study in data.get("studies", []):
        protocol = study.get("protocolSection", {})
        identification = protocol.get("identificationModule", {})
        status = protocol.get("statusModule", {})
        description = protocol.get("descriptionModule", {})
        extracted_trials.append({
            "NCT_ID": identification.get("nctId", "N/A"),
            "Title": identification.get("briefTitle", "N/A"),
            "Status": status.get("overallStatus", "N/A"),
            "Summary": description.get("briefSummary", "No summary provided."),
            "source_platform": "ClinicalTrials.gov"
        })
    return extracted_trials

def search_clinical_trials(search_term: str, limit: int = 5) -> str:
    """
    Searches ClinicalTrials.gov for studies matching a medical/clinical term (Cached 24h).
    """
    res = _fetch_clinical_trials(search_term=search_term, limit=limit)
    return truncate_tool_output(res, max_chars=1200)