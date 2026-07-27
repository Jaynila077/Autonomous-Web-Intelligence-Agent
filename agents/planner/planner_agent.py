import os
from typing import List
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq

from schemas.state import AgentState 


class GoalDecomposition(BaseModel):
    """Schema for forcing the LLM to output exactly 2-4 sub-tasks."""
    sub_tasks: List[str] = Field(
        description="A list of 2 to 4 independent sub-tasks required to fulfill the user's research query.",
        min_items=2,
        max_items=4
    )

def planner_node(state: AgentState) -> dict:
    """
    Planner Agent: Breaks down the original query into sub-tasks.
    
    Input: state.original_query
    Output: Appends to state.plan
    """
    query = state.original_query
    
    if not query:
        raise ValueError("original_query is missing from AgentState.")

   
    llm = ChatGroq(
        temperature=0, 
        model_name="llama3-70b-8192",
        api_key=os.environ.get("GROQ_API_KEY")
    )
    
   
    structured_llm = llm.with_structured_output(GoalDecomposition)
    
    system_prompt = (
        "You are an expert OSINT Planner within an autonomous intelligence system. "
        "Your objective is to analyze the user's query and break it down into exactly "
        "2 to 4 logical, independent sub-tasks for targeted web research and intelligence gathering."
    )
    
    try:
        response = structured_llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Target Query: {query}"}
        ])
        extracted_plan = response.sub_tasks
    except Exception as e:
        print(f"Error during Planner LLM execution: {e}")
        extracted_plan = [] 

    return {"plan": extracted_plan}