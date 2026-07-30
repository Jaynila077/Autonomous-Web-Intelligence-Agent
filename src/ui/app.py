import os
import streamlit as st
import requests

st.set_page_config(
    page_title="AWIS OSINT Control Tower",
    page_icon="🛸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Glassmorphism Aesthetic Styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #4F46E5, #06B6D4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    .sub-header {
        color: #94A3B8;
        font-size: 1.05rem;
        margin-bottom: 25px;
    }
    .metric-card {
        background-color: #1E293B;
        border-radius: 12px;
        padding: 15px;
        border: 1px solid #334155;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">🛸 AWIS Autonomous Intelligence Control Tower</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">DeepAgents Multi-Domain OSINT & Autonomous Web Discovery System</p>', unsafe_allow_html=True)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api/v1")

# Sidebar Controls & System Metrics
with st.sidebar:
    st.image("https://img.icons8.com/isometric-folders/100/radar.png", width=70)
    st.subheader("System Status")
    st.success("🟢 Subagents Active (4/4)")
    st.caption("Planner • Researcher • Verifier • Reporter")
    
    st.divider()
    st.subheader("Domain Tools Coverage")
    st.markdown("• 🎓 Academic & PubMed\n• 🌐 Web, Tavily & SearXNG\n• 💻 GitHub & StackOverflow\n• 🎬 YouTube Transcripts\n• 🤖 Reddit & Fediverse OSINT")

# Main Interface Tabs
tab1, tab2 = st.tabs(["🚀 Launch Research Task", "📚 Historical Intelligence Reports"])

with tab1:
    st.subheader("Target Query Dispatch")
    query = st.text_input(
        "Enter target research topic / OSINT query:",
        placeholder="e.g. Latest engineering challenges in vector databases or Agentic AI architectures"
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        run_button = st.button("🛸 Dispatch Pipeline", type="primary", use_container_width=True)
        
    if run_button and query:
        st.info(f"Submitting query to FastAPI backend: '{query}'...")
        try:
            res = requests.post(f"{BACKEND_URL}/query", json={"query": query}, timeout=5)
            if res.status_code == 200:
                st.success("Task dispatched to AWIS DeepAgents pipeline! Monitoring execution...")
                st.toast("Pipeline task created successfully!")
            else:
                st.error(f"Failed to start task: {res.text}")
        except Exception as e:
            st.error(f"Cannot connect to FastAPI backend at {BACKEND_URL}. Ensure 'python -m src.api.main' is running.\nDetails: {str(e)}")

with tab2:
    st.subheader("Generated Intelligence Reports Archive")
    
    try:
        reports_res = requests.get(f"{BACKEND_URL}/reports", timeout=5)
        if reports_res.status_code == 200:
            reports_list = reports_res.json().get("reports", [])
            
            if reports_list:
                selected_report = st.selectbox(
                    "Select a report to view:",
                    options=reports_list,
                    format_func=lambda x: f"📄 {x}"
                )
                
                if selected_report:
                    report_detail = requests.get(f"{BACKEND_URL}/reports/{selected_report}", timeout=5).json()
                    content = report_detail.get("report", "")
                    
                    st.divider()
                    st.download_button(
                        label="📥 Download Markdown Report",
                        data=content,
                        file_name=selected_report,
                        mime="text/markdown"
                    )
                    st.markdown(content)
            else:
                st.warning("No historical reports found in workspace yet.")
        else:
            st.warning("Could not fetch reports list from API.")
    except Exception as e:
        st.info(f"Backend offline or loading workspace directly...")
        reports_dir = os.path.abspath("./workspace/reports")
        if os.path.exists(reports_dir):
            files = [f for f in os.listdir(reports_dir) if f.endswith(".md")]
            files.sort(reverse=True)
            if files:
                selected = st.selectbox("Select local report:", files)
                with open(os.path.join(reports_dir, selected), "r", encoding="utf-8") as f:
                    local_content = f.read()
                st.markdown(local_content)
