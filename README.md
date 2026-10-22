# Autonomous Web Intelligence System (AWIS)

**AWIS** is a production-grade, multi-agent Open-Source Intelligence (OSINT) and deep research platform. AWIS orchestrates specialized autonomous subagents across distributed **FastMCP** microservices to plan, scrape, verify, and synthesize cited intelligence reports with automated PDF export and email delivery.

AWIS automates deep open-source research by coordinating four specialized agents to plan queries, gather live data across the web and academic sources, verify claims, and generate cited intelligence reports. Instead of stitching together manual searches or trusting unverified LLM outputs, teams get audited PDF briefs delivered straight to their inbox.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white) ![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white) ![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?logo=langchain&logoColor=white) ![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)

<!-- ![AWIS demo](docs/demo.gif) -->

**Highlights:**
- **Architecture decisions:** Decoupled 20+ research tools across 5 independent FastMCP SSE microservices (`8001`–`8005`) and built a semantic tool router that injects only the top 4 relevant tools per run to prevent context bloat across the 4-subagent (`Planner`, `Researcher`, `Verifier`, `Reporter`) workflow.
- **Safety & guardrails:** Implemented pre-flight and post-flight NeMo Guardrails for input jailbreak detection, off-topic filtering, PII redaction, and output hallucination/toxicity audits, paired with a dedicated Verifier subagent that checks source credibility.
- **Reliability & persistence:** Engineered non-blocking background job execution with FastAPI, ARQ, and Redis, backed by PostgreSQL (SQLModel + Alembic migrations), a multi-provider LLM fallback factory (NVIDIA NIM, Groq, GitHub Models, Gemini, OpenRouter), and real-time SSE status streaming.

---

## Key Features

* **Hierarchical Multi-Agent Orchestration:** Powered by `deepagents` and LangChain, a Lead Orchestrator coordinates four isolated subagents (**Planner**, **Researcher**, **Verifier**, and **Reporter**) operating over a job-scoped Virtual Filesystem (VFS).
* **Distributed FastMCP Microservices Suite:** Decouples 20+ specialized research tools across 5 independent Server-Sent Events (SSE) MCP servers (`8001`–`8005`) covering live web search, academic literature, software repositories, social/community sentiment, and document extraction.
* **Intelligent Semantic Tool Router:** Dynamically scores query intent against tool capability profiles (`select_dynamic_tools`) and injects only the top 4 most relevant tools per run to eliminate schema bloat and context noise.
* **Defense-in-Depth Safety Rails:** Pre-flight and post-flight **NeMo Guardrails** enforce input jailbreak detection, off-topic filtering, PII redaction, and output hallucination/toxicity checks.
* **Asynchronous Task Queue & Real-Time Streaming:** **FastAPI** backend paired with **ARQ** and **Redis** (Upstash/Local) for non-blocking background execution, **PostgreSQL** (NeonDB) with **SQLModel** & **Alembic** for persistence, and **SSE** for real-time agent status updates to the **Streamlit** UI.
* **Automated Deliverables & Observability:** End-to-end **Langfuse** tracing, DiskCache caching layer, automated Markdown-to-PDF compilation (`xhtml2pdf`), and Gmail SMTP report delivery.

---

## System Architecture

```text
+-----------------------------------------------------------------------------------+
|                                  Streamlit Web UI                                 |
|                         (JWT Auth, Live SSE Progress, PDF)                        |
+-----------------------------------------+-----------------------------------------+
                                          | REST / SSE
                                          v
+-----------------------------------------------------------------------------------+
|                              FastAPI Backend (Port 8000)                          |
|                    PostgreSQL (NeonDB)  <-->  Redis Queue (ARQ)                   |
+-----------------------------------------+-----------------------------------------+
                                          | Async Job Dispatch
                                          v
+-----------------------------------------------------------------------------------+
|                         AWIS Production Intelligence Pipeline                     |
|                                                                                   |
|  1. Pre-Flight NeMo Guardrails (Input Check, Off-Topic Filter, PII Redaction)     |
|  2. Semantic Tool Router (Selects Top-4 Domain Tools for Query Intent)            |
|  3. Multi-Agent Orchestrator (deepagents + Job-Scoped Workspace VFS):             |
|       ├── Planner    -> Structured 4-domain research strategy                     |
|       ├── Researcher -> Executes live MCP tools (Max 5-6 targeted calls)          |
|       ├── Verifier   -> Audits claims, statistics, & source credibility           |
|       └── Reporter   -> Synthesizes cited Markdown intelligence brief             |
|  4. Post-Flight NeMo Guardrails (Hallucination & Toxicity Audit)                  |
|  5. Artifact Generation (Job-Scoped .md + Styled PDF + Gmail SMTP Dispatch)       |
+-----------------------------------------+-----------------------------------------+
                                          | SSE Transport (langchain-mcp-adapters)
                                          v
+-----------------------------------------------------------------------------------+
|                           FastMCP Microservices Suite                             |
|  :8001 Researcher  | :8002 Academic | :8003 Developer | :8004 Social | :8005 PDF  |
+-----------------------------------------------------------------------------------+
```

---

## Multi-Provider LLM Factory

AWIS features a fault-tolerant LLM factory (`src/core/llm/factory.py`) that automatically prioritizes available credentials in your `.env`:

1. **NVIDIA NIM (`integrate.api.nvidia.com`):** Primary engine running `nvidia/nemotron-3.5-super-vl-120b-a12b` (configurable via `NVIDIA_MODEL`).
2. **Groq LPU (`api.groq.com`):** High-speed inference with live model validation and custom tool-call parsing (`ToolParsingChatGroq`).
3. **GitHub Models (`models.inference.ai.azure.com`):** Fallback routing via `GITHUB_TOKEN` (`gpt-4o-mini`).
4. **Google Gemini:** Supported via `GEMINI_API_KEY` (`gemini-1.5-flash`).
5. **OpenRouter:** Supported via `OPENROUTER_API_KEY` (`qwen/qwen-2.5-72b-instruct`).

---

## FastMCP Microservices & Tool Registry

All external scraping and extraction tools are isolated into 5 FastMCP servers launched via `src/mcp_servers/run_all.py`:

| Server | Port | Core Tools Provided |
| :--- | :--- | :--- |
| **Researcher Server** | `8001` | `search_tavily`, `search_web_news`, `search_exa_semantic`, `find_working_searxng`, `search_site_content`, `find_site_feeds`, `fetch_wiki_data`, `monitor_rss_feed` |
| **Academic Server** | `8002` | `search_arxiv`, `search_arxiv_papers`, `search_clinical_trials` |
| **Developer Server** | `8003` | `search_github_repos`, `search_stackexchange` |
| **Media & Social Server** | `8004` | `search_youtube_transcripts`, `search_youtube_transcripts_no_key`, `search_mastodon`, `search_lemmy` |
| **Extractor Server** | `8005` | `extract_pdf_with_pdfplumber`, `extract_pdf`, `extract_webpage`, `extract_wikipedia_summary`, `save_intelligence_report` |

---

## Repository Structure

```text
Autonomous-Web-Intelligence-Agent/
├── awis.py                         # Cross-platform CLI process manager (macOS/Linux/Windows)
├── start_awis.sh / .ps1            # Startup scripts for MCP, FastAPI, ARQ, and Streamlit
├── stop_awis.sh / .ps1             # Graceful shutdown scripts for all background processes
├── restart_test_part1.py           # Phase 4 persistence test: pre-restart job submission
├── restart_test_part2.py           # Phase 4 persistence test: post-restart recovery check
├── environment.yml                 # Minimal Conda blueprint (Python 3.11 + pip)
├── requirements.txt                # Locked PyPI dependencies + custom MCP adapter fork
├── .env.example                    # Environment configuration template
├── config/                         # NeMo Guardrails configurations
│   ├── actions.py                  # Custom guardrail actions
│   ├── config.yml                  # Guardrail model & rail flow definitions
│   ├── prompts.yml                 # Self-check input/output/hallucination prompts
│   └── rails.co                    # Colang guardrail definitions
├── migrations/                     # Alembic database schema migrations
└── src/
    ├── api/                        # FastAPI backend & asynchronous worker
    │   ├── main.py                 # FastAPI app initialization & CORS
    │   ├── router.py               # REST & SSE streaming endpoints
    │   ├── auth.py                 # JWT authentication & password hashing
    │   ├── database.py             # SQLModel ORM models (User, Conversation, Job, Message)
    │   ├── schemas.py              # Pydantic request/response schemas
    │   ├── worker.py               # Background job execution, PDF export & email dispatch
    │   └── arq_worker.py           # ARQ worker settings & Redis connection pool
    ├── core/                       # Core intelligence engine
    │   ├── agent/                  # DeepAgents orchestrator & subagent builder
    │   ├── llm/                    # Multi-provider LLM factory, Groq patches & token logger
    │   ├── pipeline/               # End-to-end execution runner with retries & Langfuse
    │   └── guardrails_wrapper.py   # Async NeMo Guardrails service wrapper
    ├── mcp_servers/                # 5 FastMCP SSE servers & unified launcher (run_all.py)
    ├── tools/                      # Domain tool implementations, DiskCache, PDF & SMTP tools
        └── ui/
        ├── app.py                  # Primary Streamlit frontend interface
        └── app2.py                 # Alternative Streamlit frontend interface
```

---

## Getting Started

### 1. Prerequisites
* **Conda** (Miniconda or Anaconda)
* **Git**
* **Redis** (Local Redis server running on port `6379` or an **Upstash Redis** cloud connection URL)
* **PostgreSQL** (**NeonDB** serverless Postgres connection URL or local PostgreSQL instance)

### 2. Environment Setup
We use a clean split between Conda (for Python version isolation) and Pip (for package management) to prevent dependency redundancy:

```bash
# 1. Clone the repository
git clone https://github.com/Jaynila077/Autonomous-Web-Intelligence-Agent.git
cd Autonomous-Web-Intelligence-Agent

# 2. Create and activate the Conda environment
conda env create -f environment.yml
conda activate awis

# 3. Install all Python dependencies (including the custom langchain-mcp-adapters fork)
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy the example environment template to `.env` and populate your credentials:

```bash
cp .env.example .env
```

Key settings in `.env`:
* **Database & Queue:** Set `DATABASE_URL` (PostgreSQL) and `UPSTASH_REDIS_URL` (Redis).
* **Pipeline Mode:** Set `MOCK_AGENT=false` to run the live multi-agent pipeline (or `true` to test API/queue flows without consuming API credits).
* **LLM Provider:** Set `NVIDIA_API_KEY` (and optionally `NVIDIA_MODEL=nvidia/nemotron-3.5-super-vl-120b-a12b`) and `GROQ_API_KEY` (used by NeMo Guardrails in `config/config.yml` and as the secondary LLM fallback).
* **Search Tools:** Set `TAVILY_API_KEY`, `EXA_API_KEY`, `GITHUB_TOKEN`, and `YOUTUBE_API_KEY`.
* **Email Delivery (Optional):** Provide `GMAIL_ADDRESS` and a 16-character Google `GMAIL_APP_PASSWORD` to receive PDF reports automatically via email.
* **Observability (Optional):** Add `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` for trace logging.

### 4. Database Migrations
Initialize or upgrade your PostgreSQL schema using Alembic:

```bash
alembic upgrade head
```

---

## Running the AWIS Stack

Use the unified cross-platform CLI runner (`awis.py`) to boot or terminate the entire microservice architecture (5 FastMCP servers, FastAPI backend, ARQ worker, and Streamlit UI):

### Start All Services
```bash
python awis.py start
```
* **Streamlit Web UI:** `http://localhost:8501`
* **FastAPI Backend & Docs:** `http://localhost:8000` (`http://localhost:8000/docs`)
* **FastMCP Servers:** `http://localhost:8001/sse` through `http://localhost:8005/sse`

### Stop All Services
```bash
python awis.py stop
```

### Running the Pipeline Directly via CLI
For standalone testing without the web UI or task queue (requires the 5 MCP servers to be running):
```bash
python -m src.mcp_servers.run_all
# In a second terminal (with conda activate awis):
python -m src.core.pipeline.runner "Latest advances in Vision-Language Models"
```

---

## Running Tests

Execute the test suite using `pytest`:

```bash
pytest
```

---

## Project Team

* **[Jay Nila](https://github.com/Jaynila077)**
* **[Mahak Gupta](https://github.com/Mahak753)**
* **[Manan Garg](https://github.com/MananGarg15)**
* **[Sourav Gaur](https://github.com/SouravGaur)**
* **Swarup Patil**
