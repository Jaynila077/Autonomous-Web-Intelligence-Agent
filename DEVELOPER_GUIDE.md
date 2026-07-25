# AWIS Developer Onboarding & AI Workflow Guide

Based on the reference document "DEVELOPER_GUIDE.pdf".

## 1. Core Development Rules (Read Before Coding)
1. **The Shared State is Holy:** The AgentState Pydantic model (`schemas/state.py`) is the single source of truth. All agents read from and append data to this central object. Do not modify this file without explicit approval from Dev 1 (Lead).
2. **Strict Folder Boundaries:** You are ONLY permitted to create or modify files inside your assigned directory (e.g., `src/agents/scout/`). Do not touch other developers' files.
3. **No Direct Agent-to-Agent Calls:** Agents must NEVER call each other directly.
4. **Mock Before You Integrate:** Always build a standalone test script (e.g., `test_scout.py`) with mock data to ensure your logic works before integrating with the main orchestrator in `main.py`.

## 2. How to Set Up Your AI Assistant
Before you ask your AI tool to write any code, you must give it the Master System Prompt. This ensures the AI understands the architectural constraints of the project.

### STEP A: Apply the Master System Prompt
`docs/SYSTEM_SHARED_STATE.md`
Copy and paste content of this file into your AI's custom instructions, system prompt, or initial chat context.

### STEP B: Apply Your Personal Task Prompt
Find your specific role below. Copy the prompt and give it to your AI assistant to start generating your code.

*   **DEV 2: Planner & Scope Scout (Jay)**
    *   **Your Boundary:** `agents/scout/`
    *   **Your Goal:** Break down the query and find target URLs.
    *   **Your AI Prompt:** `docs/DEV2_PLANNER_SCOUT.md`
*   **DEV 3: Extractor Engine & Knowledge Store (Sourav and Swarup)**
    *   **Your Boundary:** `agents/extractor/` and `src/storage/`
    *   **Your Goal:** Scrape the web URLs, clean the text into Markdown, and store it.
    *   **Your AI Prompt:** `docs/DEV3_EXTRACTOR_DB.md`
*   **DEV 4: Verifier Agent & Audit Loop (MANAN)**
    *   **Your Boundary:** `agents/verifier/`
    *   **Your Goal:** Extract facts and run an LLM audit to drop hallucinations.
    *   **Your AI Prompt:** `docs/DEV4_VERIFIER.md`
*   **DEV 5: Reporter Agent & UI (MAHAK)**
    *   **Your Boundary:** `agents/reporter/` and `src/ui/`
    *   **Your Goal:** Synthesize the verified facts into a final report and build the dashboard.
    *   **Your AI Prompt:** `docs/DEV5_REPORTER.md`

## 3. Daily Git Workflow
To avoid merge conflicts, strictly follow this routine:

1. **Start of Session:**
   ```bash
   git checkout main
   git pull origin main
   ```
2. **Work Locally:** Build and test your code in your specific `/src/agents/...` folder.
3. **Run your tests:** Make sure `python agents/<your_module>/test_<your_module>.py` runs successfully.
4. **Commit & Push:**
   ```bash
   git add .
   git commit -m "feat(module_name): added core logic and passing mock tests"
   git push origin main
   ```
