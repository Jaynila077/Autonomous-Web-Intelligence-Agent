import streamlit as st
import requests

st.set_page_config(page_title="AWIS Control Tower", layout="wide")

st.title("🛸 AWIS Autonomous Intelligence System")
st.caption("DeepAgents Multi-Agent Execution & OSINT Pipeline")

query = st.text_input("Enter your research goal / target query:", placeholder="e.g., Investigate solid-state battery supply chain disruptions")

if st.button("Run Intelligence Search"):
    if query:
        st.info(f"Submitting query to FastAPI backend: '{query}'")
        res = requests.post("http://localhost:8000/api/v1/query", json={"query": query})
        if res.status_code == 200:
            st.success("Task dispatched to DeepAgents pipeline! Monitoring execution...")
        else:
            st.error("Failed to start task.")

st.divider()
if st.button("Fetch Latest Final Report"):
    res = requests.get("http://localhost:8000/api/v1/report")
    if res.status_code == 200:
        st.markdown(res.json()["report"])
    else:
        st.warning("No completed report found in workspace.")
