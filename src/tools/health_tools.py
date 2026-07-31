import requests
from langchain_core.tools import tool
from typing import List, Dict, Any

@tool
def search_clinical_trials(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Searches the official ClinicalTrials.gov API to fetch recent and ongoing clinical trials 
    based on a medical search term.
    
    Use this tool when researching medical advancements, public health interventions, 
    drug efficacy, or experimental treatments. It returns authoritative, structured data 
    straight from the government registry.
    
    Args:
        query (str): The medical condition, treatment, drug name, or clinical term to search for (e.g., 'mRNA vaccine' or 'Type 2 Diabetes').
        limit (int, optional): The maximum number of clinical trials to retrieve. Defaults to 5.
        
    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing the extracted clinical trials. Each dictionary contains:
            - NCT_ID (str): The unique National Clinical Trial identifier.
            - Title (str): The brief, readable title of the study.
            - Status (str): The current overall status of the trial (e.g., 'RECRUITING', 'COMPLETED', 'ACTIVE_NOT_RECRUITING').
            - Summary (str): A brief description or abstract of the clinical trial's purpose and methodology.
            
        If no trials are found, returns an empty list. If an API error occurs, returns a list containing a single dictionary with an 'error' key.
    """
    url = "https://clinicaltrials.gov/api/v2/studies"
    
    params = {
        "query.term": query,
        "pageSize": limit,
        "format": "json"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        extracted_trials = []
        
        # Parse the structured JSON data
        for study in data.get("studies", []):
            protocol = study.get("protocolSection", {})
            identification = protocol.get("identificationModule", {})
            status = protocol.get("statusModule", {})
            description = protocol.get("descriptionModule", {})
            
            extracted_trials.append({
                "NCT_ID": identification.get("nctId", "N/A"),
                "Title": identification.get("briefTitle", "N/A"),
                "Status": status.get("overallStatus", "N/A"),
                "Summary": description.get("briefSummary", "No summary provided.")
            })
            
        return extracted_trials

    except requests.exceptions.RequestException as e:
        return [{"error": f"Error fetching data from ClinicalTrials.gov API: {str(e)}"}]
    except Exception as e:
        return [{"error": f"An unexpected error occurred: {str(e)}"}]