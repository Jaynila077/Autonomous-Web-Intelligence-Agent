import os
import markdown2
from weasyprint import HTML
from groq import Groq

from schemas.state import AgentState

class ReporterAgent:
    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is missing.")
            
        self.client = Groq(api_key=self.api_key)
        self.model = "llama3-70b-8192" 

    def run(self, state: AgentState) -> AgentState:
        """
        Reads from AgentState, generates the report, updates AgentState, and returns it.
        No direct agent-to-agent calls.
        """
        if not state.verified_claims:
            state.final_report = "No verified claims found to generate a report."
            return state

        # 1. Synthesize the context from verified claims
        claims_context = self._format_claims_for_prompt(state.verified_claims)

        # 2. Construct the system prompt enforcing the Discrepancy & Intelligence Brief structure
        prompt = f"""
        You are an expert OSINT Intelligence Synthesizer. 
        Based on the user's original query and the verified claims provided by the Verifier Agent, generate a structured Discrepancy & Intelligence Brief.

        Original Query: "{state.original_query}"

        Verified Claims Data:
        {claims_context}

        Format the output strictly in Markdown with the following sections:
        # Intelligence Brief
        ## Executive Summary
        ## Key Verified Findings
        ## Confidence Ratings (Note any discrepancies or unverified data)
        ## Source Citations (Must be hyperlinked URLs)
        
        Keep the tone objective, analytical, and highly professional.
        """

        # 3. Call Groq API
        response = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
            temperature=0.2 # Low temperature for factual synthesis
        )

        generated_md = response.choices[0].message.content

        # 4. Update the single source of truth (AgentState)
        state.final_report = generated_md

        return state

    def _format_claims_for_prompt(self, claims: list) -> str:
        """Helper to structure Pydantic claims into a readable string for the LLM."""
        formatted = ""
        for i, claim in enumerate(claims, 1):
            formatted += f"--- Claim {i} ---\n"
            formatted += f"Finding: {getattr(claim, 'claim_text', 'N/A')}\n"
            formatted += f"Verified: {getattr(claim, 'is_verified', False)}\n"
            formatted += f"Confidence Score: {getattr(claim, 'confidence_score', 0)}/10\n"
            formatted += f"Source URL: {getattr(claim, 'source_url', 'No URL')}\n\n"
        return formatted

    def export_artifacts(self, state: AgentState, output_dir: str = "output"):
        """Exports the generated state.final_report to Markdown and PDF."""
        if not getattr(state, 'final_report', None):
            print("No final report to export.")
            return

        os.makedirs(output_dir, exist_ok=True)
        md_path = os.path.join(output_dir, "report.md")
        pdf_path = os.path.join(output_dir, "report.pdf")

        # Export Markdown
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(state.final_report)

        # Convert Markdown to HTML, then to PDF via WeasyPrint
        html_content = markdown2.markdown(state.final_report)
        # Adding a bit of basic CSS so the PDF looks presentable
        styled_html = f"""
        <html><head><style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }}
            h1 {{ color: #2c3e50; }}
            h2 {{ color: #34495e; border-bottom: 1px solid #ccc; padding-bottom: 5px; }}
            a {{ color: #2980b9; }}
        </style></head><body>{html_content}</body></html>
        """
        HTML(string=styled_html).write_pdf(pdf_path)
        
        print(f"Report exported to:\n- {md_path}\n- {pdf_path}")