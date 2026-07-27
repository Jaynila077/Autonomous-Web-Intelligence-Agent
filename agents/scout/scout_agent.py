import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq

from schemas.state import AgentState, ScoutLink

# ---------------------------------------------------------
# 1. Pydantic Schemas for Metadata
# ---------------------------------------------------------
class SearchMetadataItem(BaseModel):
    """Schema for individual search metadata results."""
    title: str = Field(description="Title of the search result or web resource.")
    url: str = Field(description="Direct URL link to the resource.")
    snippet: str = Field(description="Brief summary snippet or description from search metadata.")
    scope_category: str = Field(description="Scope category used to fetch this result.")

class TaskMetadataResult(BaseModel):
    """Schema for metadata collected per sub-task."""
    sub_task: str
    assigned_scope: str = Field(description="Tool scope chosen (e.g., tech_osint, academic, news, general)")
    results: List[SearchMetadataItem] = Field(
        description="List of metadata items (title, url, snippet) retrieved for this sub-task."
    )

class ToolScopeDecision(BaseModel):
    """Schema for LLM tool selection decision."""
    scope: str = Field(
        description="Selected search scope. Options: 'tech_osint', 'academic', 'news', 'general'."
    )
    search_query: str = Field(
        description="Optimized query string to pass to the metadata tool."
    )


def fetch_metadata_by_scope(scope: str, search_query: str) -> List[Dict[str, str]]:
   
    # tools from web-scope-extract
    return 
    


def scout_node(state: AgentState) -> dict:
    plan = getattr(state, "plan", [])
    if not plan:
        raise ValueError("plan is empty or missing from AgentState. Planner must execute first.")

    llm = ChatGroq(
        temperature=0,
        model_name="llama3-70b-8192",
        api_key=os.environ.get("GROQ_API_KEY")
    )
    scope_selector_llm = llm.with_structured_output(ToolScopeDecision)

    system_prompt = (
        "You are an expert OSINT Scout Routing Agent. "
        "Analyze the provided sub-task and select the best tool search scope. "
        "Valid scopes are: 'tech_osint' (vulnerabilities/code/exploits), "
        "'academic' (papers/whitepapers), 'news' (recent reporting), or 'general' (all undefined/other topics). "
        "Formulate an optimized search query string for metadata retrieval."
    )

    scouted_links: List[ScoutLink] = []

    for task in plan:
        try:
            decision = scope_selector_llm.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Sub-Task: {task}"}
            ])

            metadata_items = fetch_metadata_by_scope(
                scope=decision.scope,
                search_query=decision.search_query
            )

            for item in metadata_items:
                scouted_links.append(ScoutLink(
                    url=item["url"],
                    title=item["title"],
                    scope_type=item["scope_category"],
                    snippet=item["snippet"],
                ))

        except Exception as e:
            print(f"Error during Scout routing for task '{task}': {e}")
            
    return {"scouted_links": scouted_links}

