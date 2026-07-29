import time
import requests
import streamlit as st

API_BASE_URL = "http://localhost:8000/api/v1"

st.set_page_config(page_title="AWIS OSINT Dashboard", layout="wide")

if "page" not in st.session_state:
    st.session_state.page = "query_page"
if "current_query" not in st.session_state:
    st.session_state.current_query = ""
if "report_markdown" not in st.session_state:
    st.session_state.report_markdown = ""

# ==========================================
# PAGE 1: QUERY SUBMISSION
# ==========================================
if st.session_state.page == "query_page":
    st.title("Autonomous Web Intelligence Agent")
    st.subheader("Targeted OSINT & Research Pipeline")

    query_input = st.text_area(
        "Enter Research Topic or Intelligence Goal:",
        placeholder="e.g., Analyze recent supply chain disruptions in the semiconductor industry.",
        height=120,
    )

    if st.button("Launch Autonomous Pipeline", type="primary"):
        if not query_input.strip():
            st.warning("Please enter a valid research query.")
        else:
            try:
                response = requests.post(
                    f"{API_BASE_URL}/query", 
                    json={"query": query_input},
                    timeout=10
                )
                response.raise_for_status()

                st.session_state.current_query = query_input
                st.session_state.page = "result_page"
                st.rerun()

            except requests.exceptions.RequestException as e:
                st.error(f"Failed to connect to backend API: {e}")

# ==========================================
# PAGE 2: PIPELINE EXECUTION & RESULT VIEW
# ==========================================
elif st.session_state.page == "result_page":
    st.title("Intelligence Briefing")
    st.caption(f"**Active Directive:** {st.session_state.current_query}")

    if st.button("← New Research Query"):
        st.session_state.page = "query_page"
        st.session_state.report_markdown = ""
        st.rerun()

    st.markdown("---")

    if not st.session_state.report_markdown:
        with st.status("Agent Crew Executing... ", expanded=True) as status:
            max_attempts = 60  # Timeout after 3 minutes (3s * 60)
            for attempt in range(max_attempts):
                try:
                    res = requests.get(f"{API_BASE_URL}/report", timeout=10).json()
                    if res.get("status") == "completed" and res.get("content"):
                        st.session_state.report_markdown = res["content"]
                        status.update(label="Intelligence Brief Complete!", state="complete", expanded=False)
                        st.rerun()
                        break
                except Exception:
                    pass
                time.sleep(3)
            else:
                status.update(label="Pipeline timed out.", state="error")
                st.error("Report generation took too long. Check your backend terminal for agent errors.")

    if st.session_state.report_markdown:
        st.markdown(st.session_state.report_markdown)