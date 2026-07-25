# TASK INSTRUCTIONS: Developer 3 (Extractor & Knowledge Store)

## Objective
Build the Extraction Engine and Vector Database Ingestion Pipeline.
- Takes links gathered by Dev 2, extracts clean Markdown content, and pushes chunks into the Vector DB.

## Inputs & Outputs
- **Input:** `state.scouted_links` (List[ScoutLink]) from `AgentState`.
- **Output:** Append extracted data to `state.extracted_data` and persist embeddings in Qdrant/Chroma.

## Required Responsibilities
1. **Extraction Routing:** Iterate through `scouted_links`. 
   - Fetch web pages using Jina Reader API (`https://r.jina.ai/<URL>`) or Trafilatura.
   - Clean HTML tags, navigation bars, and ads. Convert to clean Markdown.
2. **Sanity Check:** Mark pages with <150 words or 403 errors as `status = "FAILED"`.
3. **Vector Database Ingestion:** Chunk valid Markdown (`chunk_size=500`, `overlap=50`) and insert vectors into Qdrant/Chroma.
4. **State Update:** Append valid extractions to `state.extracted_data`.

## Code Boundary
You must ONLY write code inside `/agents/extractor/` and `/src/storage/`.

## Mock Test Interface
Provide a standalone test script `test_extractor.py` that accepts dummy `scouted_links` and returns populated `extracted_data`.