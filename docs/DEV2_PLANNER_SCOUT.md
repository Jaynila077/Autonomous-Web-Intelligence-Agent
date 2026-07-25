# TASK INSTRUCTIONS: Developer 2 (Planner & Scope Scout)

## Objective
Build the Planner and Scout module. 
- The **Planner** breaks down a user query into sub-tasks.
- The **Scout** parses each sub-task, assigns a scope, and uses `web-scope-extract` / search tools to gather target metadata and URLs.

## Inputs & Outputs
- **Input:** `state.original_query` (string) from `AgentState`.
- **Output:** Append objects to `state.plan` and `state.scouted_links`.

## Required Responsibilities
1. **Goal Decomposition:** Use an LLM call with structured output to split `original_query` into 2-4 sub-task strings.
2. **Intent & Scope Mapping:** For each sub-task, map it to a defined scope (e.g., `OFFICIAL_PR`, `NEWS`, `COMMUNITY_FORUM`).
3. **Execution:** Call `web-scope-extract` or search APIs based on the mapped scope to collect top 3-5 target links per task.
4. **State Update:** Populate `scouted_links` with `url`, `title`, `scope_type`, and `snippet`.

## Code Boundary
You must ONLY write code inside the `/agents/scout/` directory.

## Mock Test Interface
Provide a standalone test script `test_scout.py` that takes a hardcoded query string and returns populated `plan` and `scouted_links` matching `AgentState`.