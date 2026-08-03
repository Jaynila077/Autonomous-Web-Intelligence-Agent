# frontend/app.py
import os
import time
import json
import requests
import streamlit as st

# ============================================================================
# CONFIGURATION & ENVIRONMENT
# ============================================================================

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(
    page_title="AWIS // Terminal OSINT Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if "token" not in st.session_state:
    st.session_state.token = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "email" not in st.session_state:
    st.session_state.email = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "active_job_id" not in st.session_state:
    st.session_state.active_job_id = None

# ============================================================================
# CUSTOM CSS LAYER (CYBER / TERMINAL AESTHETIC)
# ============================================================================

CYBER_TERMINAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Share+Tech+Mono&display=swap');

/* Global Reset & Typography */
html, body, [class*="css"] {
    font-family: 'JetBrains Mono', 'Share Tech Mono', Consolas, monospace !important;
}

/* Background & Main Surface */
.stApp {
    background-color: #080c10;
    color: #e0e6ed;
}

/* Terminal Glass Containers */
.stCard, div[data-testid="stForm"] {
    background-color: #0d131a !important;
    border: 1px solid #1a2330 !important;
    border-radius: 2px !important;
    box-shadow: 0 0 15px rgba(0, 255, 157, 0.03) !important;
}

/* Sidebar Custom Styling */
section[data-testid="stSidebar"] {
    background-color: #05080c !important;
    border-right: 1px solid #161f2c !important;
}

section[data-testid="stSidebar"] .stButton > button {
    border-radius: 2px !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}

/* Accent Button Styles */
.stButton > button {
    background-color: #0b1612 !important;
    color: #00ff9d !important;
    border: 1px solid #00ff9d !important;
    border-radius: 2px !important;
    font-family: 'JetBrains Mono', monospace !important;
    transition: all 0.2s ease-in-out !important;
}

.stButton > button:hover {
    background-color: #00ff9d !important;
    color: #05080c !important;
    box-shadow: 0 0 10px rgba(0, 255, 157, 0.5) !important;
}

/* Input Elements Override */
.stTextInput input, .stTextArea textarea {
    background-color: #0a0f16 !important;
    color: #00ff9d !important;
    border: 1px solid #1e2a38 !important;
    border-radius: 2px !important;
    font-family: 'JetBrains Mono', monospace !important;
}

.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #00ff9d !important;
    box-shadow: 0 0 8px rgba(0, 255, 157, 0.3) !important;
}

/* Custom Message Thread Styling */
.user-msg-box {
    background-color: #0e1722;
    border-left: 3px solid #00b8ff;
    padding: 12px 16px;
    margin-bottom: 16px;
    border-radius: 2px;
    box-shadow: inset 0 0 10px rgba(0, 184, 255, 0.05);
}

.user-msg-header {
    font-size: 0.75rem;
    color: #00b8ff;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 4px;
    font-weight: 700;
}

.assistant-msg-box {
    background-color: #0a111a;
    border-left: 3px solid #00ff9d;
    padding: 16px;
    margin-bottom: 20px;
    border-radius: 2px;
    box-shadow: inset 0 0 15px rgba(0, 255, 157, 0.03);
}

.assistant-msg-header {
    font-size: 0.75rem;
    color: #00ff9d;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
    font-weight: 700;
}

/* Live Terminal Status Monitor Card */
.terminal-status-card {
    background-color: #06090e;
    border: 1px solid #00ff9d;
    padding: 16px;
    margin: 12px 0 20px 0;
    border-radius: 2px;
    position: relative;
    box-shadow: 0 0 12px rgba(0, 255, 157, 0.15);
}

.terminal-status-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #14241d;
    padding-bottom: 8px;
    margin-bottom: 12px;
}

.terminal-status-title {
    color: #00ff9d;
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.terminal-radar-pulse {
    display: inline-block;
    width: 8px;
    height: 8px;
    background-color: #00ff9d;
    border-radius: 50%;
    box-shadow: 0 0 8px #00ff9d;
    animation: radar-blink 1.2s infinite;
}

@keyframes radar-blink {
    0% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.3; transform: scale(0.85); }
    100% { opacity: 1; transform: scale(1); }
}

.terminal-stage-text {
    color: #e0e6ed;
    font-size: 0.95rem;
    font-weight: 600;
}

.terminal-agent-text {
    color: #8899a6;
    font-size: 0.8rem;
    margin-top: 4px;
}

/* Terminal Error State Box */
.terminal-error-card {
    background-color: #1a080a;
    border: 1px solid #ff3344;
    padding: 16px;
    margin: 12px 0 20px 0;
    border-radius: 2px;
    box-shadow: 0 0 12px rgba(255, 51, 68, 0.15);
}

.terminal-error-title {
    color: #ff3344;
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
}

/* Scrollbar Customization */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: #05080c;
}
::-webkit-scrollbar-thumb {
    background: #1e2a38;
    border-radius: 1px;
}
::-webkit-scrollbar-thumb:hover {
    background: #00ff9d;
}
</style>
"""

st.markdown(CYBER_TERMINAL_CSS, unsafe_allow_html=True)

# ============================================================================
# API UTILITIES & ISOLATED MOCK STUBS
# ============================================================================

def get_auth_headers():
    """Build Authorization header for protected backend endpoints."""
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}


def check_backend_health():
    """Probes the FastAPI /health endpoint to verify connectivity."""
    try:
        resp = requests.get(f"{API_BASE_URL}/health", timeout=2)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def get_fake_chat_history():
    """
    ISOLATED STUB FUNCTION: Temporary mock list for sidebar history.
    Isolate behind this single function so swapping with a real GET /api/v1/queries/
    endpoint later requires modifying only this block.
    """
    return [
        {"job_id": "job_01", "title": "[OSINT] Vector DB Scaling Bottlenecks", "timestamp": "14:20 IST"},
        {"job_id": "job_02", "title": "[AUDIT] Model Context Protocol Security", "timestamp": "11:05 IST"},
        {"job_id": "job_03", "title": "[SCOUT] Web Scraper Anti-Bot Countermeasures", "timestamp": "YESTERDAY"},
    ]

# ============================================================================
# COMPONENT: LOGIN / REGISTER SCREEN
# ============================================================================

def render_login_screen():
    st.markdown("<h2 style='color: #00ff9d; letter-spacing: 1.5px;'>AWIS // INTELLIGENCE TERMINAL</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #8899a6; font-size: 0.85rem;'>AUTONOMOUS WEB INTELLIGENCE & FACT-CHECKING ENGINE</p>", unsafe_allow_html=True)
    st.divider()

    # Verify Backend Connectivity
    if not check_backend_health():
        st.markdown(
            f"""
            <div class='terminal-error-card'>
                <div class='terminal-error-title'>SYSTEM ALERT: BACKEND UNREACHABLE</div>
                <div style='color: #e0e6ed; font-size: 0.85rem;'>
                    Unable to establish HTTP handshake with API Gateway at <code>{API_BASE_URL}</code>.<br/>
                    Ensure your Uvicorn service is operational: <code>python -m src.api.main</code>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    col_center, _ = st.columns([1, 1])

    with col_center:
        st.markdown("### SYSTEM AUTHENTICATION")
        tab_login, tab_register = st.tabs(["[ AUTH // LOGIN ]", "[ REG // REGISTER ]"])

        # LOGIN TAB
        with tab_login:
            with st.form("login_form", clear_on_submit=False):
                email = st.text_input("USER IDENTITY (EMAIL)", key="login_email_input")
                password = st.text_input("ACCESS KEY (PASSWORD)", type="password", key="login_pass_input")
                submit = st.form_submit_button("AUTHENTICATE >")

                if submit:
                    if not email or not password:
                        st.error("SYSTEM ERROR: Credentials cannot be empty.")
                    else:
                        try:
                            resp = requests.post(
                                f"{API_BASE_URL}/auth/login",
                                json={"email": email, "password": password},
                                timeout=5,
                            )
                            if resp.status_code == 200:
                                data = resp.json()
                                st.session_state.token = data["access_token"]
                                st.session_state.user_id = data["user_id"]
                                st.session_state.email = email
                                st.success("ACCESS GRANTED. Initializing session...")
                                time.sleep(0.5)
                                st.rerun()
                            elif resp.status_code == 401:
                                st.error("ACCESS DENIED: Invalid email or password credentials.")
                            else:
                                st.error(f"AUTHENTICATION ERROR ({resp.status_code}): {resp.text}")
                        except requests.RequestException as exc:
                            st.error(f"NETWORK FAILURE: Could not connect to Auth Gateway ({exc})")

        # REGISTER TAB
        with tab_register:
            with st.form("register_form", clear_on_submit=False):
                reg_email = st.text_input("NEW USER EMAIL", key="reg_email_input")
                reg_password = st.text_input("NEW PASSWORD (MIN 8 CHARS)", type="password", key="reg_pass_input")
                submit_reg = st.form_submit_button("REGISTER ACCOUNT >")

                if submit_reg:
                    if not reg_email or not reg_password:
                        st.error("SYSTEM ERROR: Email and password fields required.")
                    elif len(reg_password) < 8:
                        st.error("SECURITY POLICY: Password must be at least 8 characters long.")
                    else:
                        try:
                            resp = requests.post(
                                f"{API_BASE_URL}/auth/register",
                                json={"email": reg_email, "password": reg_password},
                                timeout=5,
                            )
                            if resp.status_code == 201:
                                data = resp.json()
                                st.session_state.token = data["access_token"]
                                st.session_state.user_id = data["user_id"]
                                st.session_state.email = reg_email
                                st.success("USER ACCOUNT CREATED. Auto-authenticating...")
                                time.sleep(0.5)
                                st.rerun()
                            elif resp.status_code == 400:
                                st.error("REGISTRATION FAILURE: Email identity is already registered.")
                            else:
                                st.error(f"REGISTRATION ERROR ({resp.status_code}): {resp.text}")
                        except requests.RequestException as exc:
                            st.error(f"NETWORK FAILURE: Could not connect to Auth Gateway ({exc})")

# ============================================================================
# COMPONENT: SIDEBAR TERMINAL CONTROL
# ============================================================================

def render_sidebar():
    with st.sidebar:
        st.markdown("<h3 style='color: #00ff9d; margin-bottom: 0;'>AWIS // SIDEBAR</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: #8899a6; font-size: 0.75rem;'>UID: {st.session_state.user_id}</p>", unsafe_allow_html=True)
        st.divider()

        # "+ New Chat" Action
        if st.button("[+] NEW INTEL SESSION", use_container_width=True):
            st.session_state.messages = []
            st.session_state.active_job_id = None
            st.rerun()

        st.markdown("<p style='color: #00ff9d; font-size: 0.8rem; margin-top: 20px;'>HISTORICAL INTEL LOGS</p>", unsafe_allow_html=True)
        st.caption("Temporary Mock History // Pending Backend GET /queries/ Endpoint")

        # Isolated Mock Chat History Rendering
        for chat in get_fake_chat_history():
            if st.button(f"📄 {chat['title']}", key=f"sidebar_{chat['job_id']}", use_container_width=True):
                st.info("Historical query loading will activate when GET /api/v1/queries/ lands.")

        st.divider()

        # System Connectivity Indicator
        if check_backend_health():
            st.markdown("<span style='color: #00ff9d; font-size: 0.75rem;'>● API GATEWAY ONLINE</span>", unsafe_allow_html=True)
        else:
            st.markdown("<span style='color: #ff3344; font-size: 0.75rem;'>● API GATEWAY OFFLINE</span>", unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

        # Logout Action
        if st.button("TERMINATE SESSION [LOGOUT]", use_container_width=True):
            st.session_state.token = None
            st.session_state.user_id = None
            st.session_state.email = None
            st.session_state.messages = []
            st.session_state.active_job_id = None
            st.rerun()

# ============================================================================
# CORE WORKER EXECUTION & IN-PLACE STATUS POLLING
# ============================================================================

def poll_job_status_and_fetch_report(job_id: str, status_stream_url: str, report_download_url: str) -> dict:
    """
    Executes in-place terminal status polling using st.empty() placeholders.
    Updates stage metrics in real time without causing Streamlit reruns or UI glitching.
    """
    status_placeholder = st.empty()
    completed = False
    final_result = {"success": False, "content": "", "error": None}

    token = st.session_state.token
    # Construct dual-auth URL for compatibility with SSE endpoint parameter fallback
    sse_auth_url = f"{API_BASE_URL}{status_stream_url}?token={token}"

    while not completed:
        try:
            # Poll status directly via short-timeout GET request on the status endpoint
            resp = requests.get(sse_auth_url, stream=True, timeout=3)

            if resp.status_code == 200:
                for line in resp.iter_lines():
                    if line:
                        decoded_line = line.decode("utf-8")
                        if decoded_line.startswith("data:"):
                            payload_str = decoded_line.replace("data:", "").strip()
                            data = json.loads(payload_str)

                            current_status = data.get("status", "UNKNOWN")
                            current_agent = data.get("current_agent", "Initializing")

                            # Render in-place terminal status card
                            status_placeholder.markdown(
                                f"""
                                <div class='terminal-status-card'>
                                    <div class='terminal-status-header'>
                                        <div class='terminal-status-title'>ACTIVE PIPELINE MONITOR // {job_id}</div>
                                        <div class='terminal-radar-pulse'></div>
                                    </div>
                                    <div class='terminal-stage-text'>STAGE: <span style='color: #00ff9d;'>[{current_status}]</span></div>
                                    <div class='terminal-agent-text'>ACTIVE AGENT: {current_agent}</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                            if current_status == "COMPLETED":
                                completed = True
                                final_result["success"] = True
                                break
                            elif current_status == "FAILED":
                                completed = True
                                final_result["success"] = False
                                final_result["error"] = data.get("error_message", "Multi-agent pipeline execution failed.")
                                break

            elif resp.status_code in (401, 403):
                completed = True
                final_result["success"] = False
                final_result["error"] = f"Authentication failure ({resp.status_code}). Token expired or invalid."
                break
            else:
                # Retry on transient status codes
                pass

        except requests.RequestException as exc:
            # Handle brief network glitches during polling
            pass

        if not completed:
            time.sleep(1.5)

    # Clear status placeholder once terminal state is reached
    status_placeholder.empty()

    if not final_result["success"]:
        return final_result

    # Fetch final markdown report from API
    try:
        report_resp = requests.get(
            f"{API_BASE_URL}{report_download_url}",
            headers=get_auth_headers(),
            timeout=10,
        )
        if report_resp.status_code == 200:
            final_result["content"] = report_resp.text
        else:
            final_result["success"] = False
            final_result["error"] = f"Report download failed ({report_resp.status_code}): {report_resp.text}"
    except requests.RequestException as exc:
        final_result["success"] = False
        final_result["error"] = f"Network error fetching report: {exc}"

    return final_result

# ============================================================================
# COMPONENT: MAIN CHAT & QUERY INTERFACE
# ============================================================================

def render_chat_interface():
    render_sidebar()

    st.markdown("<h2 style='color: #00ff9d; margin-bottom: 0;'>AWIS // OSINT INTELLIGENCE CHAT</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #8899a6; font-size: 0.8rem;'>ENTER RESEARCH PROMPT TO DISCOVER, EXTRACT, AND AUDIT WEB DATA</p>", unsafe_allow_html=True)
    st.divider()

    # Render Existing Thread Messages
    for idx, msg in enumerate(st.session_state.messages):
        if msg["role"] == "user":
            st.markdown(
                f"""
                <div class='user-msg-box'>
                    <div class='user-msg-header'>[USER PROMPT]</div>
                    <div style='color: #e0e6ed;'>{msg['content']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            if msg.get("is_error", False):
                st.markdown(
                    f"""
                    <div class='terminal-error-card'>
                        <div class='terminal-error-title'>PIPELINE EXECUTION FAILURE</div>
                        <div style='color: #e0e6ed; font-size: 0.85rem;'>{msg['content']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                    <div class='assistant-msg-box'>
                        <div class='assistant-msg-header'>[AWIS SYNTHESIZED REPORT]</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(msg["content"])

    # Query Input Form
    with st.form("query_input_form", clear_on_submit=True):
        query_text = st.text_area(
            "COMMAND PROMPT",
            placeholder="Type your target research query (e.g. 'Latest engineering challenges with vector databases')...",
            height=80,
            label_visibility="collapsed",
        )
        col_btn, _ = st.columns([1, 4])
        with col_btn:
            submit_query = st.form_submit_button("DISPATCH AGENTS >")

    if submit_query:
        if not query_text or len(query_text.strip()) < 5:
            st.warning("SYSTEM NOTICE: Query prompt must be at least 5 characters long.")
            return

        clean_query = query_text.strip()

        # Append User Message to Thread
        st.session_state.messages.append({"role": "user", "content": clean_query})

        # Submit Query to API
        try:
            resp = requests.post(
                f"{API_BASE_URL}/api/v1/queries/",
                json={"query": clean_query, "max_retries": 2},
                headers=get_auth_headers(),
                timeout=5,
            )

            if resp.status_code == 202:
                job_data = resp.json()
                job_id = job_data["job_id"]
                status_stream_url = job_data["status_stream_url"]
                report_download_url = job_data["report_download_url"]

                # Poll status & retrieve report
                result = poll_job_status_and_fetch_report(job_id, status_stream_url, report_download_url)

                if result["success"]:
                    st.session_state.messages.append({"role": "assistant", "content": result["content"], "is_error": False})
                else:
                    st.session_state.messages.append({"role": "assistant", "content": result["error"], "is_error": True})

                st.rerun()

            elif resp.status_code == 401:
                st.error("AUTHENTICATION EXPIRED: Please log in again.")
                st.session_state.token = None
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"API SUBMISSION ERROR ({resp.status_code}): {resp.text}")

        except requests.RequestException as exc:
            st.error(f"NETWORK FAILURE: Unable to dispatch query to API Gateway ({exc})")

# ============================================================================
# MAIN ROUTER
# ============================================================================

def main():
    if not st.session_state.token:
        render_login_screen()
    else:
        render_chat_interface()


if __name__ == "__main__":
    main()