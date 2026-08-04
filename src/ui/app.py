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
/* ==========================================================================
   1. STREAMLIT CHROME & FOOTER HIDING
   ========================================================================== */
#MainMenu { visibility: hidden; }
header { visibility: hidden; }
footer { visibility: hidden; }
div[data-testid="stDecoration"] { display: none; }
div[data-testid="stStatusWidget"] { visibility: hidden; }

/* ==========================================================================
   2. CONTAINER & LAYOUT DENSITY
   ========================================================================== */
.main .block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 100% !important;
}

/* ==========================================================================
   3. BASE THEME & SCANLINE / GRID OVERLAY
   ========================================================================== */
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    font-family: 'JetBrains Mono', monospace !important;
    background-color: #080c10 !important;
    color: #e0e6ed !important;
}

/* Dual-layer background: Dark cyber grid + subtle scanlines */
[data-testid="stAppViewContainer"] {
    background-image: 
        linear-gradient(rgba(0, 255, 157, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0, 255, 157, 0.03) 1px, transparent 1px),
        linear-gradient(rgba(255, 255, 255, 0.015) 50%, rgba(0, 0, 0, 0.25) 50%);
    background-size: 30px 30px, 30px 30px, 100% 4px;
    background-attachment: fixed;
}

/* ==========================================================================
   4. NATIVE STREAMLIT COMPONENT REFINEMENTS
   ========================================================================== */
/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #0d1117 !important;
    border-right: 1px solid #161b22 !important;
}

/* Form Containers & stCard */
.stCard, div[data-testid="stForm"] {
    background-color: #0d1117 !important;
    border: 1px solid #21262d !important;
    border-radius: 6px !important;
    padding: 1.25rem !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4) !important;
}

/* Form Inputs & Textareas */
div[data-baseweb="input"], div[data-baseweb="textarea"] {
    background-color: #080c10 !important;
    border: 1px solid #30363d !important;
    border-radius: 4px !important;
    color: #00ff9d !important;
    font-family: 'JetBrains Mono', monospace !important;
}

div[data-baseweb="input"]:focus-within, div[data-baseweb="textarea"]:focus-within {
    border-color: #00ff9d !important;
    box-shadow: 0 0 8px rgba(0, 255, 157, 0.3) !important;
}

/* Buttons */
.stButton > button {
    background-color: #0d1117 !important;
    color: #00ff9d !important;
    border: 1px solid #00ff9d !important;
    border-radius: 4px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}

.stButton > button:hover {
    background-color: #00ff9d !important;
    color: #080c10 !important;
    box-shadow: 0 0 12px rgba(0, 255, 157, 0.5) !important;
}

/* Scrollbars */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #080c10; }
::-webkit-scrollbar-thumb { background: #21262d; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #00ff9d; }

/* ==========================================================================
   5. CUSTOM HTML AGENT / TERMINAL CLASSES
   ========================================================================== */
/* User Message Elements */
.user-msg-box {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-left: 3px solid #00ff9d;
    border-radius: 4px;
    padding: 1rem;
    margin-bottom: 1rem;
}

.user-msg-header {
    color: #00ff9d;
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
}

/* Assistant Message Elements */
.assistant-msg-box {
    background-color: #080c10;
    border: 1px solid #161b22;
    border-left: 3px solid #00b8ff;
    border-radius: 4px;
    padding: 1rem;
    margin-bottom: 1rem;
}

.assistant-msg-header {
    color: #00b8ff;
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
}

/* Terminal Status Cards & Indicators */
.terminal-status-card {
    background-color: #0d1117;
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 1rem;
    margin: 1rem 0;
}

.terminal-status-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
}

.terminal-status-title {
    color: #00ff9d;
    font-weight: 600;
    font-size: 0.95rem;
    letter-spacing: 0.03em;
}

/* Radar Pulse Animation */
.terminal-radar-pulse {
    width: 10px;
    height: 10px;
    background-color: #00ff9d;
    border-radius: 50%;
    display: inline-block;
    animation: radar-blink 1.5s infinite ease-in-out;
}

@keyframes radar-blink {
    0% {
        transform: scale(0.8);
        opacity: 0.3;
        box-shadow: 0 0 0 0 rgba(0, 255, 157, 0.7);
    }
    50% {
        transform: scale(1.2);
        opacity: 1;
        box-shadow: 0 0 10px 4px rgba(0, 255, 157, 0.4);
    }
    100% {
        transform: scale(0.8);
        opacity: 0.3;
        box-shadow: 0 0 0 0 rgba(0, 255, 157, 0);
    }
}

/* Terminal Stage & Agent Text */
.terminal-stage-text {
    color: #8b949e;
    font-size: 0.85rem;
}

.terminal-agent-text {
    color: #e0e6ed;
    font-size: 0.9rem;
}

/* Terminal Error Cards */
.terminal-error-card {
    background-color: rgba(255, 69, 58, 0.08);
    border: 1px solid #ff453a;
    border-radius: 6px;
    padding: 1rem;
    margin: 1rem 0;
}

.terminal-error-title {
    color: #ff453a;
    font-weight: 700;
    font-size: 0.95rem;
    margin-bottom: 0.25rem;
}

/* ==========================================================================
   6. LOGIN SCREEN & AUTH CARD ENHANCEMENTS
   ========================================================================== */
/* Startup Log Text */
.terminal-boot-log {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: rgba(0, 255, 157, 0.65);
    line-height: 1.5;
    background-color: rgba(13, 17, 23, 0.8);
    border: 1px solid #161b22;
    border-radius: 4px;
    padding: 0.75rem 1rem;
    margin-bottom: 1.25rem;
}

.terminal-boot-log .success-tag {
    color: #00ff9d;
    font-weight: 700;
}

/* Card Container Top Glow / Scanning Line */
.login-card-header {
    position: relative;
    padding-top: 6px;
    margin-bottom: 1rem;
}

.login-card-header::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, #00ff9d, transparent);
    box-shadow: 0 0 10px #00ff9d;
    animation: scan-line-glow 2.5s ease-in-out infinite;
}

@keyframes scan-line-glow {
    0%, 100% { opacity: 0.3; }
    50% { opacity: 1; }
}

/* Streamlit Tabs Customization */
button[data-baseweb="tab"] {
    background-color: #080c10 !important;
    border: 1px solid #21262d !important;
    border-bottom: none !important;
    color: #8b949e !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    padding: 0.5rem 1rem !important;
    border-radius: 4px 4px 0 0 !important;
    transition: all 0.2s ease !important;
}

button[data-baseweb="tab"]:hover {
    color: #00ff9d !important;
    border-color: #30363d !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    background-color: #0d1117 !important;
    color: #00ff9d !important;
    border-color: #00ff9d !important;
    box-shadow: inset 0 2px 0 #00ff9d !important;
}

/* Ensure tab panel connects seamlessly with tab header */
div[data-baseweb="tab-panel"] {
    padding-top: 1rem !important;
}

/* ==========================================================================
   7. SIDEBAR COMPONENT REFINEMENTS
   ========================================================================== */
/* Terminal User ID Status Readout */
.sidebar-uid-readout {
    background-color: #080c10;
    border: 1px solid #21262d;
    border-left: 3px solid #00ff9d;
    border-radius: 4px;
    padding: 0.4rem 0.6rem;
    font-size: 0.75rem;
    color: #8b949e;
    letter-spacing: 0.05em;
    margin-top: 0.25rem;
    margin-bottom: 0.75rem;
}

.sidebar-uid-readout span {
    color: #00ff9d;
    font-weight: 700;
}

/* Custom Styled Terminal Dividers */
.cyber-divider {
    height: 1px;
    background: linear-gradient(90deg, #161b22, #30363d, #161b22);
    margin: 1.25rem 0;
}

/* Marker CSS (hidden elements used purely for DOM targeting) */
.btn-marker {
    display: none !important;
}

/* Primary "New Session" Button Targeting */
div[data-testid="stSidebar"] div.element-container:has(> .btn-marker-new-session) + div.element-container div.stButton > button {
    background-color: rgba(0, 255, 157, 0.08) !important;
    border: 1px solid #00ff9d !important;
    color: #00ff9d !important;
    font-weight: 700 !important;
    box-shadow: 0 0 10px rgba(0, 255, 157, 0.15) !important;
}

div[data-testid="stSidebar"] div.element-container:has(> .btn-marker-new-session) + div.element-container div.stButton > button:hover {
    background-color: #00ff9d !important;
    color: #080c10 !important;
    box-shadow: 0 0 15px rgba(0, 255, 157, 0.4) !important;
}

/* Logout Button Targeting */
div[data-testid="stSidebar"] div.element-container:has(> .btn-marker-logout) + div.element-container div.stButton > button {
    border: 1px solid #ff453a !important;
    color: #ff453a !important;
    background-color: rgba(255, 69, 58, 0.05) !important;
}

div[data-testid="stSidebar"] div.element-container:has(> .btn-marker-logout) + div.element-container div.stButton > button:hover {
    background-color: #ff453a !important;
    color: #080c10 !important;
    box-shadow: 0 0 12px rgba(255, 69, 58, 0.4) !important;
}

/* Historical Chat Item Metadata Card Wrapper */
.sidebar-history-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.7rem;
    color: #8b949e;
    margin-top: -0.5rem;
    margin-bottom: 0.6rem;
    padding: 0 0.25rem;
}

.sidebar-history-meta .history-tag {
    color: #00ff9d;
    opacity: 0.7;
}

/* System Gateway Status Badges */
.gateway-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.3rem 0.6rem;
    border-radius: 4px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.05em;
}

.gateway-badge.online {
    background-color: rgba(0, 255, 157, 0.1);
    border: 1px solid rgba(0, 255, 157, 0.3);
    color: #00ff9d;
}

.gateway-badge.offline {
    background-color: rgba(255, 51, 68, 0.1);
    border: 1px solid rgba(255, 51, 68, 0.3);
    color: #ff3344;
}

.gateway-indicator-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
}

.gateway-badge.online .gateway-indicator-dot {
    background-color: #00ff9d;
    box-shadow: 0 0 6px #00ff9d;
}

.gateway-badge.offline .gateway-indicator-dot {
    background-color: #ff3344;
    box-shadow: 0 0 6px #ff3344;
}

/* ==========================================================================
   8. CHAT INTERFACE & MARKDOWN REPORT STYLING
   ========================================================================== */
/* Marker CSS (hidden element used purely for DOM targeting) */
.report-marker {
    display: none !important;
}

/* Fade/Slide-In Entrance Animation for Messages */
@keyframes msg-slide-in {
    from {
        opacity: 0;
        transform: translateY(12px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.user-msg-box, .assistant-msg-box, .terminal-error-card {
    animation: msg-slide-in 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    margin-bottom: 1.5rem !important; /* Spacing rhythm between consecutive messages */
}

/* Identity Badge Pills inside Message Headers */
.msg-identity-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.15rem 0.45rem;
    border-radius: 3px;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    margin-right: 0.5rem;
}

.msg-identity-badge.user {
    background-color: rgba(0, 255, 157, 0.12);
    border: 1px solid rgba(0, 255, 157, 0.35);
    color: #00ff9d;
}

.msg-identity-badge.awis {
    background-color: rgba(0, 184, 255, 0.12);
    border: 1px solid rgba(0, 184, 255, 0.35);
    color: #00b8ff;
}

.msg-identity-badge.error {
    background-color: rgba(255, 69, 58, 0.12);
    border: 1px solid rgba(255, 69, 58, 0.35);
    color: #ff453a;
}

/* ==========================================================================
   SCOPED MARKDOWN REPORT STYLING (TARGETS ONLY REPORT CONTENT FOLLOWING .report-marker)
   ========================================================================== */
/* Base Text Container */
div.element-container:has(> .report-marker) + div.element-container div[data-testid="stMarkdownContainer"] {
    font-family: 'JetBrains Mono', monospace !important;
    color: #e0e6ed !important;
    line-height: 1.6 !important;
}

/* Headings inside generated reports */
div.element-container:has(> .report-marker) + div.element-container div[data-testid="stMarkdownContainer"] h1,
div.element-container:has(> .report-marker) + div.element-container div[data-testid="stMarkdownContainer"] h2,
div.element-container:has(> .report-marker) + div.element-container div[data-testid="stMarkdownContainer"] h3 {
    color: #00ff9d !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    letter-spacing: 0.03em !important;
    border-bottom: 1px solid #21262d !important;
    padding-bottom: 0.3rem !important;
    margin-top: 1.25rem !important;
    margin-bottom: 0.75rem !important;
}

div.element-container:has(> .report-marker) + div.element-container div[data-testid="stMarkdownContainer"] h4,
div.element-container:has(> .report-marker) + div.element-container div[data-testid="stMarkdownContainer"] h5 {
    color: #00b8ff !important;
    font-weight: 600 !important;
    margin-top: 1rem !important;
}

/* Bullet & Numbered Lists */
div.element-container:has(> .report-marker) + div.element-container div[data-testid="stMarkdownContainer"] ul,
div.element-container:has(> .report-marker) + div.element-container div[data-testid="stMarkdownContainer"] ol {
    padding-left: 1.25rem !important;
    margin-bottom: 1rem !important;
}

div.element-container:has(> .report-marker) + div.element-container div[data-testid="stMarkdownContainer"] li {
    margin-bottom: 0.35rem !important;
}

div.element-container:has(> .report-marker) + div.element-container div[data-testid="stMarkdownContainer"] li::marker {
    color: #00ff9d !important;
}

/* Tables */
div.element-container:has(> .report-marker) + div.element-container div[data-testid="stMarkdownContainer"] table {
    width: 100% !important;
    border-collapse: collapse !important;
    margin: 1rem 0 !important;
    font-size: 0.85rem !important;
    background-color: #0d1117 !important;
    border: 1px solid #21262d !important;
    border-radius: 4px !important;
    overflow: hidden !important;
}

div.element-container:has(> .report-marker) + div.element-container div[data-testid="stMarkdownContainer"] th {
    background-color: #161b22 !important;
    color: #00ff9d !important;
    text-align: left !important;
    padding: 0.6rem 0.8rem !important;
    border-bottom: 1px solid #30363d !important;
    font-weight: 700 !important;
}

div.element-container:has(> .report-marker) + div.element-container div[data-testid="stMarkdownContainer"] td {
    padding: 0.5rem 0.8rem !important;
    border-bottom: 1px solid #161b22 !important;
    color: #e0e6ed !important;
}

div.element-container:has(> .report-marker) + div.element-container div[data-testid="stMarkdownContainer"] tr:hover td {
    background-color: rgba(0, 255, 157, 0.03) !important;
}

/* Blockquotes */
div.element-container:has(> .report-marker) + div.element-container div[data-testid="stMarkdownContainer"] blockquote {
    background-color: #0d1117 !important;
    border-left: 3px solid #00ff9d !important;
    padding: 0.6rem 1rem !important;
    margin: 1rem 0 !important;
    color: #8b949e !important;
    font-style: italic !important;
    border-radius: 0 4px 4px 0 !important;
}

/* Inline & Block Code */
div.element-container:has(> .report-marker) + div.element-container div[data-testid="stMarkdownContainer"] code {
    background-color: #161b22 !important;
    color: #00ff9d !important;
    padding: 0.15rem 0.35rem !important;
    border-radius: 3px !important;
    border: 1px solid #30363d !important;
    font-size: 0.85em !important;
}

div.element-container:has(> .report-marker) + div.element-container div[data-testid="stMarkdownContainer"] pre {
    background-color: #0d1117 !important;
    border: 1px solid #21262d !important;
    border-radius: 4px !important;
    padding: 0.8rem !important;
}

div.element-container:has(> .report-marker) + div.element-container div[data-testid="stMarkdownContainer"] pre code {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
}

/* ==========================================================================
   9. ACTIVE PIPELINE STEPPER & MONITOR STYLING
   ========================================================================== */
.terminal-stepper-container {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 1.25rem 0 1rem 0;
    position: relative;
    width: 100%;
}

/* Individual Stage Node */
.stepper-node {
    display: flex;
    flex-direction: column;
    align-items: center;
    position: relative;
    z-index: 2;
    flex: 1;
}

/* Circle Indicator */
.stepper-circle {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.7rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    transition: all 0.2s ease;
}

/* Node Label */
.stepper-label {
    font-size: 0.68rem;
    font-family: 'JetBrains Mono', monospace;
    margin-top: 0.4rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    text-align: center;
}

/* Stage State: COMPLETED */
.stepper-node.completed .stepper-circle {
    background-color: #00ff9d;
    color: #080c10;
    box-shadow: 0 0 8px rgba(0, 255, 157, 0.4);
}
.stepper-node.completed .stepper-label {
    color: #00ff9d;
}

/* Stage State: ACTIVE (Pulsing continuous glow) */
.stepper-node.active .stepper-circle {
    background-color: #080c10;
    border: 2px solid #00ff9d;
    color: #00ff9d;
    box-shadow: 0 0 12px #00ff9d;
    animation: stepper-active-pulse 1.5s infinite ease-in-out;
}
.stepper-node.active .stepper-label {
    color: #ffffff;
    text-shadow: 0 0 6px rgba(0, 255, 157, 0.6);
}

@keyframes stepper-active-pulse {
    0%, 100% {
        box-shadow: 0 0 6px rgba(0, 255, 157, 0.4);
        border-color: #00ff9d;
    }
    50% {
        box-shadow: 0 0 16px rgba(0, 255, 157, 0.9);
        border-color: #70ffc4;
    }
}

/* Stage State: PENDING */
.stepper-node.pending .stepper-circle {
    background-color: #0d1117;
    border: 1px solid #30363d;
    color: #484f58;
}
.stepper-node.pending .stepper-label {
    color: #484f58;
}

/* Connector Line between Nodes */
.stepper-connector {
    position: absolute;
    top: 12px;
    left: 10%;
    right: 10%;
    height: 2px;
    background-color: #21262d;
    z-index: 1;
}

.stepper-connector-progress {
    height: 100%;
    background: linear-gradient(90deg, #00ff9d, #00b8ff);
    transition: width 0.3s ease;
}

/* Agent Active Readout Bar */
.terminal-agent-status-bar {
    background-color: #080c10;
    border: 1px solid #161b22;
    border-radius: 4px;
    padding: 0.5rem 0.75rem;
    font-size: 0.78rem;
    color: #8b949e;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.terminal-agent-status-bar .agent-highlight {
    color: #00b8ff;
    font-weight: 700;
}

/* ==========================================================================
   EDGE CASE STEPPER STATES (FAILED & UNKNOWN)
   ========================================================================== */
/* Stage State: FAILED (Red highlight matching error card #ff453a) */
.stepper-node.failed .stepper-circle {
    background-color: #080c10;
    border: 2px solid #ff453a;
    color: #ff453a;
    box-shadow: 0 0 12px rgba(255, 69, 58, 0.6);
    animation: stepper-failed-pulse 1.5s infinite ease-in-out;
}

.stepper-node.failed .stepper-label {
    color: #ff453a;
    text-shadow: 0 0 6px rgba(255, 69, 58, 0.5);
}

@keyframes stepper-failed-pulse {
    0%, 100% {
        box-shadow: 0 0 6px rgba(255, 69, 58, 0.4);
        border-color: #ff453a;
    }
    50% {
        box-shadow: 0 0 16px rgba(255, 69, 58, 0.9);
        border-color: #ff7b72;
    }
}

/* Connector bar color override for failed state */
.stepper-connector-progress.failed-bar {
    background: linear-gradient(90deg, #00ff9d, #ff453a) !important;
}

/* Stage State: UNKNOWN / UNRECOGNIZED (Neutral Amber) */
.stepper-node.unknown .stepper-circle {
    background-color: #080c10;
    border: 2px solid #d29922;
    color: #d29922;
    box-shadow: 0 0 8px rgba(210, 153, 34, 0.4);
}

.stepper-node.unknown .stepper-label {
    color: #d29922;
}

/* ==========================================================================
   10. QUERY INPUT FORM & TERMINAL COMMAND PROMPT STYLING
   ========================================================================== */
/* Marker CSS (hidden element used purely for DOM targeting) */
.query-form-marker {
    display: none !important;
}

/* Cyber Form Card Wrapper */
div[data-testid="stForm"]:has(.query-form-marker) {
    background-color: #0d1117 !important;
    border: 1px solid #00ff9d !important;
    border-radius: 6px !important;
    padding: 1.25rem !important;
    box-shadow: 0 0 15px rgba(0, 255, 157, 0.12) !important;
    position: relative !important;
    margin-top: 1rem !important;
}

/* Terminal Input Prompt Label & Blinking Cursor */
.terminal-input-prompt-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    font-weight: 700;
    color: #00ff9d;
    margin-bottom: 0.5rem;
    letter-spacing: 0.05em;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}

.terminal-input-prompt-label .prompt-symbol {
    color: #00ff9d;
    font-weight: 900;
}

.terminal-input-prompt-label .blinking-cursor {
    display: inline-block;
    color: #00ff9d;
    font-weight: 900;
    animation: terminal-cursor-blink 1s infinite steps(2, start);
}

@keyframes terminal-cursor-blink {
    0%, 100% { opacity: 0; }
    50% { opacity: 1; }
}

/* Form Textarea Inner Styling */
div[data-testid="stForm"]:has(.query-form-marker) div[data-baseweb="textarea"] {
    background-color: #080c10 !important;
    border: 1px solid #21262d !important;
    border-radius: 4px !important;
    color: #e0e6ed !important;
    font-family: 'JetBrains Mono', monospace !important;
    padding: 0.5rem !important;
}

div[data-testid="stForm"]:has(.query-form-marker) div[data-baseweb="textarea"]:focus-within {
    border-color: #00ff9d !important;
    box-shadow: 0 0 10px rgba(0, 255, 157, 0.25) !important;
}

/* Execute / Dispatch Button connected styling */
div[data-testid="stForm"]:has(.query-form-marker) div.stButton > button {
    background-color: rgba(0, 255, 157, 0.1) !important;
    border: 1px solid #00ff9d !important;
    color: #00ff9d !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    letter-spacing: 0.05em !important;
    margin-top: 0.25rem !important;
    transition: all 0.2s ease !important;
    width: 100% !important;
}

div[data-testid="stForm"]:has(.query-form-marker) div.stButton > button:hover {
    background-color: #00ff9d !important;
    color: #080c10 !important;
    box-shadow: 0 0 15px rgba(0, 255, 157, 0.5) !important;
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

    # System Boot Sequence Logs
    st.markdown(
        """
        <div class='terminal-boot-log'>
            [SYS_INIT] INITIALIZING AWIS CORE SUBSYSTEMS... <span class='success-tag'>[OK]</span><br/>
            [SYS_INIT] LOADING OSINT RECONNAISSANCE MODULES... <span class='success-tag'>[OK]</span><br/>
            [NET_GATEWAY] ESTABLISHING ENCRYPTED SESSION HANDSHAKE... <span class='success-tag'>[OK]</span><br/>
            [AUTH_GATEWAY] SECURITY PROTOCOLS ACTIVE // READY FOR USER AUTHENTICATION
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_center, _ = st.columns([1, 1])

    with col_center:
        # Animated top scan line indicator
        st.markdown("<div class='login-card-header'></div>", unsafe_allow_html=True)
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
        # Zone 1: Header & Session Controls
        st.markdown("<h3 style='color: #00ff9d; margin-bottom: 0;'>AWIS // SIDEBAR</h3>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class='sidebar-uid-readout'>
                SYS_USER // <span>{st.session_state.user_id}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Primary Action Button
        st.markdown("<div class='btn-marker btn-marker-new-session'></div>", unsafe_allow_html=True)
        if st.button("[+] NEW INTEL SESSION", key="btn_new_session", use_container_width=True):
            st.session_state.messages = []
            st.session_state.active_job_id = None
            st.rerun()

        # Zone Separator 1 -> 2
        st.markdown("<div class='cyber-divider'></div>", unsafe_allow_html=True)

        # Zone 2: Historical Intel Logs
        st.markdown("<p style='color: #00ff9d; font-size: 0.8rem; margin-bottom: 2px;'>HISTORICAL INTEL LOGS</p>", unsafe_allow_html=True)
        st.caption("Temporary Mock History // Pending Backend GET /queries/ Endpoint")
        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

        # Isolated Mock Chat History Iteration
        for chat in get_fake_chat_history():
            if st.button(f"📄 {chat['title']}", key=f"sidebar_{chat['job_id']}", use_container_width=True):
                st.info("Historical query loading will activate when GET /api/v1/queries/ lands.")
            
            # Timestamp & status metadata display directly under each history button
            st.markdown(
                f"""
                <div class='sidebar-history-meta'>
                    <span class='history-tag'>ID: {chat['job_id']}</span>
                    <span>🕒 {chat['timestamp']}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Zone Separator 2 -> 3
        st.markdown("<div class='cyber-divider'></div>", unsafe_allow_html=True)

        # Zone 3: System Status & Logout Action
        if check_backend_health():
            st.markdown(
                """
                <div class='gateway-badge online'>
                    <span class='gateway-indicator-dot'></span>
                    <span>API GATEWAY ONLINE</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class='gateway-badge offline'>
                    <span class='gateway-indicator-dot'></span>
                    <span>API GATEWAY OFFLINE</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

        # Logout Action Button
        st.markdown("<div class='btn-marker btn-marker-logout'></div>", unsafe_allow_html=True)
        if st.button("TERMINATE SESSION [LOGOUT]", key="btn_logout", use_container_width=True):
            st.session_state.token = None
            st.session_state.user_id = None
            st.session_state.email = None
            st.session_state.messages = []
            st.session_state.active_job_id = None
            st.rerun()

# ============================================================================
# CORE WORKER EXECUTION & IN-PLACE STATUS POLLING
# ============================================================================

def build_pipeline_stepper_html(current_status: str, last_known_idx: int = 0) -> tuple[str, int]:
    """
    Maps backend status strings to a 6-stage terminal stepper.
    
    Returns:
        tuple[str, int]: (Generated HTML string, updated active stage index)
    """
    stages = [
        ("QUEUED", "QUEUED"),
        ("SCOUTING", "SCOUT"),
        ("EXTRACTING", "EXTRACT"),
        ("AUDITING", "VERIFY"),
        ("SYNTHESIZING", "REPORT"),
        ("COMPLETED", "DONE"),
    ]

    status_upper = current_status.upper().strip()

    # Direct Explicit Failure Check
    is_failed = status_upper in ("FAILED", "ERROR", "FAILURE", "CRASHED")

    stage_order = {
        "QUEUED": 0, "PENDING": 0, "INIT": 0, "INITIALIZING": 0,
        "SCOUTING": 1, "SCOUT": 1, "PLANNING": 1, "RESEARCHING": 1,
        "EXTRACTING": 2, "EXTRACT": 2, "SCRAPING": 2,
        "AUDITING": 3, "VERIFYING": 3, "VERIFY": 3, "AUDIT": 3,
        "SYNTHESIZING": 4, "SYNTHESIZE": 4, "REPORTING": 4, "GENERATING": 4,
        "COMPLETED": 5, "SUCCESS": 5, "DONE": 5,
    }

    # Determine current stage index safely
    if is_failed:
        # Halt at the last valid processing stage before COMPLETED (defaulting to last known stage)
        current_idx = min(last_known_idx, 4)
    elif status_upper in stage_order:
        current_idx = stage_order[status_upper]
    else:
        # For unrecognized strings, preserve progress by holding at last_known_idx
        current_idx = last_known_idx

    # Calculate progress bar percentage
    progress_pct = int((current_idx / (len(stages) - 1)) * 100)
    bar_cls = "stepper-connector-progress failed-bar" if is_failed else "stepper-connector-progress"

    nodes_html = []
    for idx, (code, label) in enumerate(stages):
        if is_failed and idx == current_idx:
            # Highlight the exact stage where failure occurred
            state_cls = "failed"
            icon = "✖"
        elif is_failed and idx < current_idx:
            # Prior completed steps stay checked
            state_cls = "completed"
            icon = "✓"
        elif not is_failed and status_upper not in stage_order and idx == current_idx:
            # Unrecognized status string gets a neutral indicator
            state_cls = "unknown"
            icon = "?"
        elif idx < current_idx:
            state_cls = "completed"
            icon = "✓"
        elif idx == current_idx:
            state_cls = "active"
            icon = "●"
        else:
            state_cls = "pending"
            icon = str(idx + 1)

        nodes_html.append(
            f"""
            <div class='stepper-node {state_cls}'>
                <div class='stepper-circle'>{icon}</div>
                <div class='stepper-label'>{label}</div>
            </div>
            """
        )

    stepper_html = f"""
    <div style='position: relative;'>
        <div class='stepper-connector'>
            <div class='{bar_cls}' style='width: {progress_pct}%;'></div>
        </div>
        <div class='terminal-stepper-container'>
            {"".join(nodes_html)}
        </div>
    </div>
    """

    return stepper_html, current_idx

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

    last_known_stage = 0
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

                            # Render in-place terminal status card with pipeline stepper
                            stepper_html, last_known_stage = build_pipeline_stepper_html(current_status, last_known_stage)

                            status_placeholder.markdown(
                                f"""
                                <div class='terminal-status-card'>
                                    <div class='terminal-status-header'>
                                        <div class='terminal-status-title'>ACTIVE PIPELINE MONITOR // <span style='color: #8b949e;'>JOB:</span> {job_id}</div>
                                        <div class='terminal-radar-pulse'></div>
                                    </div>
                                    
                                    {stepper_html}

                                    <div class='terminal-agent-status-bar'>
                                        <span>⚡ ACTIVE SUBAGENT:</span>
                                        <span class='agent-highlight'>{current_agent}</span>
                                    </div>
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
                    <div class='user-msg-header'>
                        <span class='msg-identity-badge user'>👤 USER</span>
                        <span>[USER PROMPT]</span>
                    </div>
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
                        <div class='terminal-error-title'>
                            <span class='msg-identity-badge error'>⚠️ ALERT</span>
                            <span>PIPELINE EXECUTION FAILURE</span>
                        </div>
                        <div style='color: #e0e6ed; font-size: 0.85rem;'>{msg['content']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                    <div class='assistant-msg-box'>
                        <div class='assistant-msg-header'>
                            <span class='msg-identity-badge awis'>🤖 AWIS CORE</span>
                            <span>[SYNTHESIZED REPORT]</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown("<div class='report-marker'></div>", unsafe_allow_html=True)
                st.markdown(msg["content"])

    # Query Input Form
    with st.form("query_input_form", clear_on_submit=True):
        # DOM targeting marker
        st.markdown("<div class='query-form-marker'></div>", unsafe_allow_html=True)
        
        # Terminal prompt header with glyph & blinking cursor
        st.markdown(
            """
            <div class='terminal-input-prompt-label'>
                <span class='prompt-symbol'>$</span> COMMAND PROMPT <span class='blinking-cursor'>_</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

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