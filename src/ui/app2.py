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
    page_title="AWIS ResearchAssist",
    page_icon="🧠",
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
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if 'theme' not in st.session_state:
    st.session_state.theme = "light"  # Default theme

# ============================================================================
# THEME/ CSS INJECTION
# ============================================================================

def get_theme_css():
    if st.session_state.theme == "light":
        theme_vars = """
        --bg-color: #ffffff;
        --text-main: #171717;
        --border-color: #e5e5e5;
        --accent-color: #2563eb;
        --text-muted: #737373;
        --card-bg: #fafafa;
        """
    else:
        theme_vars = """
        --bg-color: #0f0f0f;
        --text-main: #e5e5e5;
        --border-color: #2a2a2a;
        --accent-color: #3b82f6;
        --text-muted: #a3a3a3;
        --card-bg: #1a1a1a;
        """

    return f"""
    <style>
        :root {{
            {theme_vars}
        }}

        /* UI Font & Backgrounds */
        .stApp, section[data-testid="stSidebar"] {{
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }}

        /* Inputs & Buttons */
        .stButton > button, .stTextInput input {{
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            color: var(--text-main) !important;
        }}
        
        .stButton > button p, .stButton > button div {{
            color: var(--text-main) !important;
        }}
        
        .stButton > button[kind="primary"] {{
            color: var(--text-main) !important;
            background-color: var(--card-bg) !important;
            border-color: var(--accent-color) !important;
        }}
        
        .stButton > button[kind="primary"] p {{
            color: var(--text-main) !important;
        }}

        /* Report Card Component */
        .report-card {{
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-left: 4px solid var(--accent-color);
            border-radius: 8px;
            padding: 32px;
            font-family: ui-monospace, 'SF Mono', 'Consolas', monospace;
            color: var(--text-main);
        }}

        .report-card .muted {{
            color: var(--text-muted);
        }}
    </style>
    """

st.markdown(get_theme_css(), unsafe_allow_html=True)

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


def fetch_conversations():
    """Fetches the list of active conversations for the current user."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/conversations/",
            headers=get_auth_headers(),
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            st.session_state.token = None
            st.rerun()
        else:
            st.sidebar.error("Failed to load conversation history.")
            return []
    except requests.RequestException as e:
        st.sidebar.error(f"Network error loading chats: {str(e)}")
        return []


def fetch_conversation_messages(conversation_id: str):
    """Loads all messages for a specific conversation thread into session state."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/conversations/{conversation_id}/messages",
            headers=get_auth_headers(),
            timeout=10,
        )
        if response.status_code == 200:
            raw_messages = response.json()
            # Map backend messages into Streamlit chat state format
            formatted_messages = []
            for msg in raw_messages:
                formatted_messages.append({
                    "role": msg["role"],
                    "content": msg["content"] or "*(Report generating...)*",
                    "is_error": False,
                })
            st.session_state.messages = formatted_messages
            st.session_state.conversation_id = conversation_id
            st.rerun()
        else:
            st.error("Could not retrieve conversation messages.")
    except requests.RequestException as e:
        st.error(f"Network error: {str(e)}")

# ============================================================================
# COMPONENT: LOGIN / REGISTER SCREEN
# ============================================================================

def render_login_screen():
    col_head, col_theme = st.columns([5, 1])
    
    with col_head:
        st.markdown("<h2 style='color: var(--text-main); letter-spacing: -0.02em; font-weight: 600;'>AWIS ResearchAssist</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color: var(--text-muted); font-size: 0.875rem;'>Log in or register to continue.</p>", unsafe_allow_html=True)
        
    with col_theme:
        theme_label = "🌙 Dark Theme" if st.session_state.theme == "light" else "☀ Light Theme"
        if st.button(theme_label, use_container_width=True):
            st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
            st.rerun()

    st.divider()

    # Verify Backend Connectivity
    if not check_backend_health():
        st.markdown(
            f"""
            <div class='report-card'>
                <h3 style='color: #ef4444; margin-top: 0; margin-bottom: 16px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;'>Error</h3>
                <div style='color: var(--text-main); font-size: 0.875rem;'>
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
        st.markdown("<h3 style='color: var(--text-main); font-size: 1.125rem; font-weight: 600; margin-bottom: 12px;'>Authentication</h3>", unsafe_allow_html=True)
        tab_login, tab_register = st.tabs(["Log In", "Register"])

        # LOGIN TAB
        with tab_login:
            with st.form("login_form", clear_on_submit=False):
                email = st.text_input("Email", key="login_email_input")
                password = st.text_input("Password", type="password", key="login_pass_input")
                submit = st.form_submit_button("Log In")

                if submit:
                    if not email or not password:
                        st.error("Error: Credentials cannot be empty.")
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
                                st.success("Success. Initializing session...")
                                time.sleep(0.5)
                                st.rerun()
                            elif resp.status_code == 401:
                                st.error("Login failed: Invalid email or password credentials.")
                            else:
                                st.error(f"Login error ({resp.status_code}): {resp.text}")
                        except requests.RequestException as exc:
                            st.error(f"Network error: Could not connect to Auth Gateway ({exc})")

        # REGISTER TAB
        with tab_register:
            with st.form("register_form", clear_on_submit=False):
                reg_email = st.text_input("Email", key="reg_email_input")
                reg_password = st.text_input("Password (min 8 characters)", type="password", key="reg_pass_input")
                submit_reg = st.form_submit_button("Register")

                if submit_reg:
                    if not reg_email or not reg_password:
                        st.error("Error: Email and password fields required.")
                    elif len(reg_password) < 8:
                        st.error("Error: Password must be at least 8 characters long.")
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
                                st.success("Account created. Auto-authenticating...")
                                time.sleep(0.5)
                                st.rerun()
                            elif resp.status_code == 400:
                                st.error("Registration failed: Email identity is already registered.")
                            else:
                                st.error(f"Registration error ({resp.status_code}): {resp.text}")
                        except requests.RequestException as exc:
                            st.error(f"Network error: Could not connect to Auth Gateway ({exc})")

# ============================================================================
# COMPONENT: SIDEBAR TERMINAL CONTROL
# ============================================================================

def render_sidebar():
    with st.sidebar:
        # App name (minimal, removed UID)
        st.markdown("<div style='font-weight: 600; font-size: 1.125rem; margin-bottom: 24px; color: var(--text-main);'>AWIS ResearchAssist</div>", unsafe_allow_html=True)
        # New Query button
        if st.button("+ New Query", use_container_width=True):
            st.session_state.messages = []
            st.session_state.active_job_id = None
            st.session_state.conversation_id = None
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # History list
        conversations = fetch_conversations()
        for conv in conversations:
            conv_id = conv.get('id')
            label = conv.get('label', '')
            
            # Truncate to ~30 chars
            truncated_label = label[:30] + '...' if len(label) > 30 else label
            
            # Check active state
            is_active = (st.session_state.get('conversation_id') == conv_id)
            
            # Use Streamlit's primary button type to isolate the active item, 
            # then inject CSS to apply the var(--accent-color) per mockup
            button_type = "primary" if is_active else "secondary"
            if is_active:
                st.markdown(
                    """<style>
                    div[data-testid="stSidebar"] button[kind="primary"] {
                        color: var(--accent-color) !important;
                        background-color: var(--card-bg) !important;
                        border-color: var(--card-bg) !important;
                        font-weight: 500 !important;
                    }
                    div[data-testid="stSidebar"] button[kind="primary"]:hover {
                        border-color: var(--accent-color) !important;
                    }
                    </style>""", 
                    unsafe_allow_html=True
                )

            # Clickable history button
            if st.button(truncated_label, key=f"hist_{conv_id}", type=button_type, use_container_width=True):
                st.session_state.conversation_id = conv_id
                fetch_conversation_messages(conv_id)
                st.rerun()

        st.markdown("---")

        # Theme Toggle
        theme_label = "🌙 Dark Theme" if st.session_state.theme == "light" else "☀ Light Theme"
        if st.button(theme_label, use_container_width=True):
            st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
            st.rerun()

        # System Connected Status
        st.markdown(
            """
            <div style="font-size: 0.75rem; color: var(--text-muted); display: flex; align-items: center; gap: 8px; margin: 12px 0 12px 8px;">
                <div style="width: 8px; height: 8px; background-color: #16a34a; border-radius: 50%;"></div>
                System Connected
            </div>
            """, 
            unsafe_allow_html=True
        )

        # Logout Button
        if st.button("Logout", use_container_width=True):
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

                            # Render in-place status card
                            status_placeholder.markdown(
                                f"""
                                <div class="report-card">
                                    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-weight: 600; margin-bottom: 12px; color: var(--text-main);">Generating report...</div>
                                    <div style="color: var(--text-main); margin-bottom: 4px;">Status: {current_status}</div>
                                    <div style="color: var(--text-muted); font-size: 0.875rem;">Current step: {current_agent}</div>
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

    # 1. Minimal Header
    st.markdown("<h1 style='font-size: 1.5rem; font-weight: 600; margin-bottom: 40px; color: var(--text-main);'>Query Results</h1>", unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 2. Render Existing Thread Messages (Latest Only)
    if not st.session_state.messages:
        st.markdown(
            "<p style='color: var(--text-muted); margin-bottom: 48px;'>Submit a query to generate a report.</p>",
            unsafe_allow_html=True,
        )
    else:
        # Find the last user and assistant messages
        last_user_msg = None
        last_assistant_msg = None
        for msg in reversed(st.session_state.messages):
            if msg["role"] == "user" and not last_user_msg:
                last_user_msg = msg
            elif msg["role"] == "assistant" and not last_assistant_msg:
                last_assistant_msg = msg

        if last_user_msg:
            st.markdown(
                f"""
                <div style="margin-bottom: 24px;">
                    <span style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); font-weight: 600; margin-bottom: 8px; display: block;">Current Query</span>
                    <p style="font-size: 1.125rem; line-height: 1.5; color: var(--text-main); margin: 0;">{last_user_msg['content']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if last_assistant_msg:
            # 3 separate markdown calls to ensure report formatting renders correctly
            st.markdown('<div class="report-card" style="margin-bottom: 48px;">', unsafe_allow_html=True)
            
            if last_assistant_msg.get("is_error", False):
                st.markdown("<h3 style='color: #ef4444; margin-top: 0; margin-bottom: 16px; font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif;'>Error</h3>", unsafe_allow_html=True)
            
            st.markdown(last_assistant_msg["content"])
            
            st.markdown('</div>', unsafe_allow_html=True)

    # 3. Query Input Form (Side-by-Side text_input + button)
    def handle_submit():
        if st.session_state.query_widget and st.session_state.query_widget.strip():
            st.session_state.pending_query = st.session_state.query_widget
            st.session_state.query_widget = ""

    if "query_widget" not in st.session_state:
        st.session_state.query_widget = ""

    is_processing = bool(st.session_state.get("active_job_id"))

    col_input, col_btn = st.columns([5, 1])
    with col_input:
        st.text_input(
            "Query",
            label_visibility="collapsed",
            placeholder="Ask a follow-up question or start a new query...",
            key="query_widget",
            on_change=handle_submit,
            disabled=is_processing
        )
    with col_btn:
        st.button("Submit", use_container_width=True, on_click=handle_submit, disabled=is_processing)
        
    if is_processing:
        st.markdown("<div style='font-size: 0.75rem; color: var(--text-muted); margin-top: 8px;'>Generating report...</div>", unsafe_allow_html=True)

    # 4. Core API Execution Logic (Preserved entirely)
    if st.session_state.get("pending_query"):
        query_text = st.session_state.pending_query
        st.session_state.pending_query = ""  # Clear after capturing to prevent rerun loops
        
        if not query_text or len(query_text.strip()) < 5:
            st.warning("Query prompt must be at least 5 characters long.")
            return

        clean_query = query_text.strip()

        # Append User Message to Thread
        st.session_state.messages.append({"role": "user", "content": clean_query})

        # Submit Query to API
        try:
            resp = requests.post(
                f"{API_BASE_URL}/api/v1/queries/",
                json={
                    "query": clean_query,
                    "conversation_id": st.session_state.conversation_id,
                    "max_retries": 2,
                },
                headers=get_auth_headers(),
                timeout=5,
            )

            if resp.status_code == 202:
                job_data = resp.json()
                job_id = job_data["job_id"]
                status_stream_url = job_data["status_stream_url"]
                report_download_url = job_data["report_download_url"]

                # Capture conversation_id returned by backend (new thread or existing)
                st.session_state.conversation_id = job_data.get("conversation_id", st.session_state.conversation_id)
                st.session_state.active_job_id = job_id

                # Poll status & retrieve report
                result = poll_job_status_and_fetch_report(job_id, status_stream_url, report_download_url)

                if result["success"]:
                    st.session_state.messages.append({"role": "assistant", "content": result["content"], "is_error": False})
                else:
                    st.session_state.messages.append({"role": "assistant", "content": result["error"], "is_error": True})

                st.session_state.active_job_id = None
                st.rerun()

            elif resp.status_code == 401:
                st.error("Authentication expired. Please log in again.")
                st.session_state.token = None
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"API submission error ({resp.status_code}): {resp.text}")

        except requests.RequestException as exc:
            st.error(f"Network error: Unable to dispatch query to API Gateway ({exc})")

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