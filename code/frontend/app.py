"""
Project AERO - AI-Enabled Regional Operations Agent
Internal Codename: itechops

A Streamlit interface for LangGraph assistants featuring IT helpdesk capabilities.

This application provides a clean web interface for interacting with LangGraph
assistants, featuring streaming responses, reasoning tags, and debug information.

IMPORTANT: Before running this client, you MUST start the LangGraph API server:
    1. Open a new terminal
    2. cd code/backend
    3. Run: langgraph dev
    4. Wait for "Ready accept requests at http://127.0.0.1:2024"
    5. Then run this client in another terminal: streamlit run app.py
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import httpx
import streamlit as st
import streamlit.components.v1 as components
from langgraph_sdk import get_sync_client

# Get project root directory
APP_PATH = Path(__file__).resolve()
PROJECT_ROOT = APP_PATH.parent.parent.parent

# Add backend directory to path for imports
sys.path.append(str(PROJECT_ROOT / "code" / "backend"))

# Import enterprise services from services directory
from services import create_ticket, assign_ticket, close_ticket

# Configure logging
LOG_DIR = PROJECT_ROOT / "storage" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            LOG_DIR / f"frontend_{datetime.now().strftime('%Y%m%d')}.log",
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)

_LOGGER = logging.getLogger(__name__)

_LOGGER.info(f"APP_PATH: {APP_PATH}")
_LOGGER.info(f"PROJECT_ROOT: {PROJECT_ROOT}")
_LOGGER.info(f"LOG_DIR: {LOG_DIR}")

# Define chat history# History directory
HISTORY_DIR = PROJECT_ROOT / "storage" / "chat_history"

# Role-specific history directories
EMPLOYEE_HISTORY_DIR = HISTORY_DIR / "employee"
ENGINEER_HISTORY_DIR = HISTORY_DIR / "engineer"

# Create directories if they don't exist
for dir_path in [HISTORY_DIR, EMPLOYEE_HISTORY_DIR, ENGINEER_HISTORY_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

_LOGGER.info(f"HISTORY_DIR: {HISTORY_DIR}")

# ==============================================================================
# Configuration and Initialization
# ==============================================================================

# LangGraph API server address
BASE_URL = os.getenv("LANGGRAPH_API_URL", "http://127.0.0.1:2024")

# Create sync client for LangGraph API communication
CLIENT = get_sync_client(url=BASE_URL)

# ==============================================================================
# Chat History Persistence Functions
# ==============================================================================
# Sample history format:
# [
#   {"role": "user", "content": "what time is it?"},
#   {"role": "ai", "content": "...", "name": null, "think": "..."},
#   {"role": "tool", "content": "...", "name": "web_search"}
# ]

def get_role_history_dir(is_engineer: bool) -> Path:
    """
    Get the history directory based on user role.

    Args:
        is_engineer: True if user is IT Support Engineer, False if Employee

    Returns:
        Path to the role-specific history directory
    """
    return ENGINEER_HISTORY_DIR if is_engineer else EMPLOYEE_HISTORY_DIR


def load_history(assistant_id: str, thread_id: str, is_engineer: bool) -> List[Dict]:
    """
    Load chat history from file based on user role.

    Args:
        assistant_id: Assistant ID used as file name prefix
        thread_id: Thread ID
        is_engineer: True if user is IT Support Engineer, False if Employee

    Returns:
        List of historical messages
    """
    history_dir = get_role_history_dir(is_engineer)
    history_file = history_dir / f"{assistant_id[:8]}_{thread_id}.json"
    _LOGGER.debug(f"Loading history from: {history_file}")
    if history_file.exists():
        try:
            with open(history_file, "r") as f:
                history = json.load(f)
                _LOGGER.debug(f"Loaded {len(history)} messages")
                return history
        except Exception as e:
            _LOGGER.error(f"Failed to load history: {e}")
            return []
    return []


def save_history(assistant_id: str, thread_id: str, history: List[Dict], is_engineer: bool):
    """
    Save chat history to file based on user role.

    Args:
        assistant_id: Assistant ID used as file name prefix
        thread_id: Thread ID
        history: List of messages to save
        is_engineer: True if user is IT Support Engineer, False if Employee
    """
    history_dir = get_role_history_dir(is_engineer)
    history_file = history_dir / f"{assistant_id[:8]}_{thread_id}.json"
    _LOGGER.debug(f"Saving {len(history)} messages to: {history_file}")
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)


def clear_all_history(assistant_id: str, is_engineer: bool):
    """
    Clear all conversation history for a specific assistant based on user role.

    Args:
        assistant_id: Assistant ID to clear history for
        is_engineer: True if user is IT Support Engineer, False if Employee
    """
    history_dir = get_role_history_dir(is_engineer)
    pattern = f"{assistant_id[:8]}_*.json"
    history_files = list(history_dir.glob(pattern))
    
    for file in history_files:
        try:
            file.unlink()
            _LOGGER.info(f"Deleted history file: {file}")
        except Exception as e:
            _LOGGER.error(f"Failed to delete history file {file}: {e}")
    
    st.session_state.history[ASSISTANT_ID] = []
    st.session_state.ticket_logs[ASSISTANT_ID] = []


def get_all_conversations(assistant_id: str, is_engineer: bool) -> List[Dict]:
    """
    Get all historical conversations for a specific assistant based on user role.

    Args:
        assistant_id: Assistant ID to filter conversation history
        is_engineer: True if user is IT Support Engineer, False if Employee

    Returns:
        List of conversation summaries with thread_id, preview, created_at, and message_count
    """
    conversations = []
    history_dir = get_role_history_dir(is_engineer)
    
    if not os.path.exists(history_dir):
        return conversations

    prefix = f"{assistant_id[:8]}_"

    for filename in os.listdir(history_dir):
        if filename.startswith(prefix) and filename.endswith(".json"):
            thread_id = filename[len(prefix) : -5]
            history_file = os.path.join(history_dir, filename)

            try:
                with open(history_file, "r") as f:
                    history = json.load(f)

                if not history:
                    continue

                preview = "Empty conversation"
                for msg in history:
                    if msg.get("role") == "user":
                        preview = msg.get("content", "")[:50]
                        if len(msg.get("content", "")) > 50:
                            preview += "..."
                        break

                created_at = os.path.getmtime(history_file)

                conversations.append(
                    {
                        "thread_id": thread_id,
                        "preview": preview,
                        "created_at": created_at,
                        "message_count": len(history),
                    }
                )
            except:
                continue

    conversations.sort(key=lambda x: x["created_at"], reverse=True)
    return conversations


# Avatar mapping for chat interface
# - "ai": Streamlit built-in "assistant" avatar (🤖)
# - "user": Streamlit built-in "user" avatar (👤)
# - "tool": Emoji icon (🛠️)
AVATARS = {"ai": "assistant", "user": "user", "tool": "🛠️"}

# Streaming mode switch - some models may not support streaming with tool calls
STREAMING = False

# ==============================================================================
# Streamlit Page Initialization
# ==============================================================================

st.set_page_config(page_title="AERO - AI-Enabled Regional Operations Agent", layout="wide", page_icon="🤖")

# Custom CSS for sidebar button alignment
st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] button[kind="secondary"] {
        justify-content: flex-start !important;
        text-align: left !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# Session State Initialization
# ==============================================================================

if "threads" not in st.session_state:
    st.session_state.threads: Dict[str, str] = {}

if "history" not in st.session_state:
    st.session_state.history: Dict[str, List[Dict[str, str]]] = {}

if "ticket_logs" not in st.session_state:
    st.session_state.ticket_logs: Dict[str, List[str]] = {}

# ==============================================================================
# Helper Function: Get Assistant List
# ==============================================================================

@st.cache_data(show_spinner=False, ttl=90)
def list_assistants() -> List[Dict[str, Any]]:
    """
    Retrieve available assistants from LangGraph API server.

    Assistant registration and discovery flow:
    1. Server reads langgraph.json config file on startup
    2. Config defines assistant names and module paths
    3. Server loads specified modules and extracts AGENT variable
    4. Assistant is registered to API service
    5. Client queries available assistants via CLIENT.assistants.search()

    Returns:
        List of assistants with assistant_id, name, and other metadata
    """
    try:
        return CLIENT.assistants.search(limit=50)
    except httpx.ConnectError:
        st.markdown(
            """
            # Connection Error 😱

            The LangGraph API server is not reachable. Please check if the server is running.
            """
        )
        st.stop()

# ==============================================================================
# Load Assistant List and Check Connection
# ==============================================================================

ALL_ASSISTANTS = list_assistants()

if not ALL_ASSISTANTS:
    st.error("❌ No assistants found on the server.")
    st.markdown(
        """
    **The LangGraph API server is not running!**

    Please start the server first:
    ```bash
    cd code/backend
    langgraph dev
    ```

    Then wait for the message: *"Ready accept requests at http://127.0.0.1:2024"*
    """
    )
    st.stop()

# ==============================================================================
# Sidebar: Role Selection and Session Management
# ==============================================================================

with st.sidebar:
    # -------------------------------------------------------------------------
    # Role Selection (Dual-role system)
    # -------------------------------------------------------------------------
    st.markdown("### 👤 Role")
    USER_ROLE = st.selectbox(
        "Select Your Role",
        ["Employee", "IT Support Engineer"],
        index=0,
        key="role_selector",
    )
    IS_ENGINEER = USER_ROLE == "IT Support Engineer"
    
    st.sidebar.markdown("---")
    
    # -------------------------------------------------------------------------
    # Assistant Selection
    # -------------------------------------------------------------------------
    ASSISTANT = st.selectbox(
        "Select Assistant",
        ALL_ASSISTANTS,
        format_func=lambda a: a.get("name") or a["assistant_id"],
    )
    ASSISTANT_ID = ASSISTANT["assistant_id"]
    
    # Check if role has changed and reset if needed (after ASSISTANT_ID is defined)
    if (
        "previous_role" in st.session_state 
        and st.session_state.previous_role != USER_ROLE
        and st.session_state.get("role_change_in_progress") != USER_ROLE
    ):
        # Set guard flag to prevent infinite loop during rerun
        st.session_state.role_change_in_progress = USER_ROLE
        
        # Reset conversation when role changes
        _LOGGER.info(f"[ROLE] Changed from {st.session_state.previous_role} to {USER_ROLE}")
        
        # Reset thread and history
        new_thread = CLIENT.threads.create()
        st.session_state.threads[ASSISTANT_ID] = new_thread["thread_id"]
        st.session_state.history[ASSISTANT_ID] = []
        
        # Clear URL params
        query_params = st.query_params.to_dict()
        for key in list(query_params.keys()):
            if key.startswith("thread_"):
                del query_params[key]
        st.query_params.clear()
        st.rerun()
    else:
        # Reset guard flag and update previous_role
        st.session_state.role_change_in_progress = None
        st.session_state.previous_role = USER_ROLE
    
    # Always update role state
    st.session_state.user_role = USER_ROLE
    st.session_state.is_engineer = IS_ENGINEER

    if st.sidebar.button("➕ New conversation", use_container_width=True):
        _LOGGER.info(f"Creating new conversation for assistant: {ASSISTANT_ID}")
        new_thread_id = CLIENT.threads.create()["thread_id"]
        st.session_state.threads[ASSISTANT_ID] = new_thread_id
        st.session_state.history[ASSISTANT_ID] = []
        st.session_state.ticket_logs[ASSISTANT_ID] = []
        st.query_params[f"thread_{ASSISTANT_ID[:8]}"] = new_thread_id
        st.rerun()

    # Determine current thread ID
    thread_id_from_url = st.query_params.get(f"thread_{ASSISTANT_ID[:8]}")
    thread_value = st.session_state.threads.get(ASSISTANT_ID)

    if thread_value is not None:
        THREAD_ID = thread_value
    elif thread_id_from_url:
        THREAD_ID = thread_id_from_url
        st.session_state.threads[ASSISTANT_ID] = THREAD_ID
    else:
        THREAD_ID = CLIENT.threads.create()["thread_id"]
        st.session_state.threads[ASSISTANT_ID] = THREAD_ID

    # Load history if not already loaded
    if (
        ASSISTANT_ID not in st.session_state.history
        or not st.session_state.history[ASSISTANT_ID]
    ):
        _LOGGER.info(f"Loading history for assistant: {ASSISTANT_ID}")
        st.session_state.history[ASSISTANT_ID] = load_history(ASSISTANT_ID, THREAD_ID, IS_ENGINEER)

    # Initialize ticket logs for this assistant
    if ASSISTANT_ID not in st.session_state.ticket_logs:
        st.session_state.ticket_logs[ASSISTANT_ID] = []

    # Sync thread ID to URL
    st.query_params[f"thread_{ASSISTANT_ID[:8]}"] = THREAD_ID

    # -------------------------------------------------------------------------
    # Conversation History List
    # -------------------------------------------------------------------------
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📜 Conversation History")

    all_conversations = get_all_conversations(ASSISTANT_ID, IS_ENGINEER)

    if all_conversations:
        # Create conversation selection using selectbox
        conversation_options = ["-- Select a conversation --"] + [f"{conv['preview']}" for conv in all_conversations]
        
        # Find if current thread is in history
        matching_idx = next((i+1 for i, conv in enumerate(all_conversations) if conv['thread_id'] == THREAD_ID), 0)
        
        selected_idx = st.sidebar.selectbox(
            "Select conversation",
            range(len(conversation_options)),
            index=matching_idx,
            format_func=lambda i: conversation_options[i],
            label_visibility="hidden",
            key="conv_selector"
        )
        
        # Handle selection change
        if selected_idx != matching_idx and selected_idx > 0:
            selected_conv = all_conversations[selected_idx - 1]
            _LOGGER.info(f"Switching to conversation: {selected_conv['thread_id']}")
            st.session_state.threads[ASSISTANT_ID] = selected_conv['thread_id']
            st.session_state.history[ASSISTANT_ID] = load_history(
                ASSISTANT_ID, selected_conv['thread_id'], IS_ENGINEER
            )
            st.query_params[f"thread_{ASSISTANT_ID[:8]}"] = selected_conv['thread_id']
            st.rerun()
        
        # Clear History button (only show when there is history)
        if st.sidebar.button("🗑️ Clear History", use_container_width=True, key="clear_history_btn"):
            clear_all_history(ASSISTANT_ID, IS_ENGINEER)
            st.rerun()
    else:
        st.sidebar.info("No conversation history")

    # -------------------------------------------------------------------------
    # Pending Tickets (IT Engineer view only)
    # -------------------------------------------------------------------------
    if IS_ENGINEER:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🎫 Pending Tickets")
        
        # Pending Tickets Data
        pending_tickets = [
            {"id": "INC-1001", "type": "Password Reset", "priority": "High", "requester": "john.doe@nvidia.com", "created": "2026-05-25 09:15", "description": "Cannot reset password, getting error when trying to reset via Okta"},
            {"id": "INC-1002", "type": "VPN Issue", "priority": "Medium", "requester": "jane.smith@nvidia.com", "created": "2026-05-25 10:30", "description": "VPN connection drops every 5 minutes when working from home"},
            {"id": "INC-1003", "type": "Software Install", "priority": "Low", "requester": "bob.wilson@nvidia.com", "created": "2026-05-25 11:45", "description": "Need help installing Microsoft Teams on laptop"},
        ]
        
        # Ticket selection
        ticket_options = [f"{ticket['id']} - {ticket['type']} ({ticket['priority']})" for ticket in pending_tickets]
        selected_ticket_str = st.sidebar.selectbox("Select a ticket to work on", ["-- Select a ticket --"] + ticket_options, key="ticket_selector")
        
        # Store selected ticket in session state and reset analysis state
        if selected_ticket_str != "-- Select a ticket --":
            selected_ticket_idx = ticket_options.index(selected_ticket_str)
            new_ticket = pending_tickets[selected_ticket_idx]
            
            # Check if ticket changed
            if not st.session_state.get("selected_ticket") or st.session_state.selected_ticket["id"] != new_ticket["id"]:
                st.session_state.ticket_analyzed = False
            
            st.session_state.selected_ticket = new_ticket
        else:
            st.session_state.selected_ticket = None
            st.session_state.ticket_analyzed = False
        
        # -------------------------------------------------------------------------
        # Operations Dashboard (IT Engineer view only)
        # -------------------------------------------------------------------------
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📈 Operations Dashboard")
        
        # IT Operational Metrics
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            st.markdown("**Ticket Automation Rate**")
            st.markdown("**42%**")
            
        with col2:
            st.markdown("**Average MTTR**")
            st.markdown("**58 mins**")
            st.markdown("<span style='color:green;font-size:12px'>↓ from 240 mins</span>", unsafe_allow_html=True)
        
        st.sidebar.markdown("**Employee Self-Service Rate**")
        st.sidebar.markdown("**51%**")
        
        st.sidebar.markdown(
            "<p style='font-size:10px;color:#666'>PoC Simulation Data | Enterprise IT Operations</p>",
            unsafe_allow_html=True
        )

# ==============================================================================
# JavaScript Container for UI interactions
# ==============================================================================

JS_CONTAINER = st.container(height=1, border=False)

# ==============================================================================
# Helper Functions: Create Message Boxes
# ==============================================================================

def _create_message_box(persona, tool_name):
    """
    Create empty message boxes and placeholders for streaming messages.

    Args:
        persona: Message role ("user", "ai", "tool")
        tool_name: Tool name (only used when persona="tool")

    Returns:
        Tuple of (reasoning_contents, message_contents) placeholders
    """
    with JS_CONTAINER:
        components.html(
            """
            <script>
            parent.document.querySelectorAll('details[open]').forEach(details => {
                details.removeAttribute('open');
            });
            </script>
            """,
            height=1,
        )
        time.sleep(0.1)

    message_box = CHAT.chat_message(AVATARS.get(persona, "🤖"))

    if persona == "tool":
        message_box = message_box.expander(f"Using {tool_name}...", expanded=False)

    return message_box.empty(), message_box.empty()


def _create_streaming_message_box(persona, tool_name):
    """
    Create message boxes for streaming messages (alias for _create_message_box).
    """
    return _create_message_box(persona, tool_name)


# ==============================================================================
# Diagnostic Tool Functions
# ==============================================================================

def generate_diagnostic_script(platform: str) -> str:
    """
    Generate platform-specific diagnostic script.

    Args:
        platform: Operating system platform ("Windows", "macOS", "Linux")

    Returns:
        Formatted diagnostic script as string
    """
    scripts = {
        "Windows": """
# Enterprise IT Helpdesk Diagnostic Script (PowerShell)
# Run with: powershell -ExecutionPolicy Bypass -File diagnose.ps1

Write-Host "=== Enterprise IT Helpdesk Diagnostic Report ===" -ForegroundColor Cyan
Write-Host "Generated: $(Get-Date)" -ForegroundColor Gray
Write-Host ""

# System Information
Write-Host "--- SYSTEM INFORMATION ---" -ForegroundColor Yellow
Get-ComputerInfo | Select-Object OSName, OSVersion, TotalPhysicalMemory, NumberOfProcessors

# Network Status
Write-Host ""
Write-Host "--- NETWORK STATUS ---" -ForegroundColor Yellow
Get-NetIPAddress | Where-Object { $_.AddressFamily -eq 'IPv4' }
Test-Connection -ComputerName google.com -Count 3

# Running Services
Write-Host ""
Write-Host "--- CRITICAL SERVICES ---" -ForegroundColor Yellow
Get-Service -Name "wuauserv", "dhcp", "dns", "lanmanworkstation" | 
    Select-Object Name, Status, StartType

# Event Logs (Recent Errors)
Write-Host ""
Write-Host "--- RECENT ERROR EVENTS ---" -ForegroundColor Yellow
Get-WinEvent -LogName System -MaxEvents 10 | Where-Object { $_.Level -ge 2 }

# Disk Usage
Write-Host ""
Write-Host "--- DISK USAGE ---" -ForegroundColor Yellow
Get-Volume | Select-Object DriveLetter, FileSystem, Size, FreeSpace

Write-Host ""
Write-Host "=== Diagnostic Complete ===" -ForegroundColor Green
""",
        "macOS": """
#!/bin/bash
# Enterprise IT Helpdesk Diagnostic Script (Bash)
# Run with: bash diagnose.sh

echo "=== Enterprise IT Helpdesk Diagnostic Report ==="
echo "Generated: $(date)"
echo ""

# System Information
echo "--- SYSTEM INFORMATION ---"
sw_vers
sysctl -n machdep.cpu.brand_string
sysctl -n hw.memsize | awk '{print $1/1024/1024/1024 " GB"}'

# Network Status
echo ""
echo "--- NETWORK STATUS ---"
ifconfig | grep -E "inet|status"
ping -c 3 google.com

# Running Services
echo ""
echo "--- CRITICAL SERVICES ---"
launchctl list | grep -E "com.apple.network|com.apple.opendirectory"

# System Logs (Recent Errors)
echo ""
echo "--- RECENT ERROR EVENTS ---"
log show --last 10m --predicate 'level == error' --style compact | head -20

# Disk Usage
echo ""
echo "--- DISK USAGE ---"
df -h /

echo ""
echo "=== Diagnostic Complete ==="
""",
        "Linux": """
#!/bin/bash
# Enterprise IT Helpdesk Diagnostic Script (Bash)
# Run with: bash diagnose.sh

echo "=== Enterprise IT Helpdesk Diagnostic Report ==="
echo "Generated: $(date)"
echo ""

# System Information
echo "--- SYSTEM INFORMATION ---"
cat /etc/os-release | grep PRETTY_NAME
uname -r
cat /proc/cpuinfo | grep "model name" | head -1
free -h | grep Mem

# Network Status
echo ""
echo "--- NETWORK STATUS ---"
ip addr show | grep inet
ping -c 3 google.com

# Running Services
echo ""
echo "--- CRITICAL SERVICES ---"
systemctl list-units --type=service --state=running | grep -E "network|sshd|ntp"

# System Logs (Recent Errors)
echo ""
echo "--- RECENT ERROR EVENTS ---"
journalctl -p err -n 10

# Disk Usage
echo ""
echo "--- DISK USAGE ---"
df -h /

echo ""
echo "=== Diagnostic Complete ==="
"""
    }
    return scripts.get(platform, "# Unknown platform")


# ==============================================================================
# Main Chat Interface
# ==============================================================================

CHAT = st.container()

# Create chat input box
if IS_ENGINEER:
    USER_INPUT = st.chat_input("💬 IT Support Console - How can I assist?")
else:
    USER_INPUT = st.chat_input("💬 How can I help you?")

# IT Engineer: Ticket Analysis Section
if IS_ENGINEER:
    # Initialize session state
    if "selected_ticket" not in st.session_state:
        st.session_state.selected_ticket = None
    if "ticket_analyzed" not in st.session_state:
        st.session_state.ticket_analyzed = False
    
    selected_ticket = st.session_state.selected_ticket
    
    if selected_ticket:
        st.markdown("---")
        
        # Display ticket details in expander
        ticket_expander = st.expander(f"📌 {selected_ticket['id']}: {selected_ticket['type']}", expanded=True)
        with ticket_expander:
            st.markdown(f"**Requester:** {selected_ticket['requester']}")
            st.markdown(f"**Created:** {selected_ticket['created']}")
            st.markdown(f"**Priority:** {selected_ticket['priority']}")
            st.markdown(f"**Description:** {selected_ticket['description']}")
        
        st.markdown("")
        
        # Analyze Ticket button with custom style
        analyze_button = st.button("🔍 Analyze Ticket", use_container_width=True, key="analyze_ticket_btn")
        
        if analyze_button:
            st.session_state.ticket_analyzed = True
        
        # Display analysis results if ticket has been analyzed
        if st.session_state.ticket_analyzed:
            st.markdown("---")
            st.markdown("### 📊 Ticket Analysis Results")
            
            # Similar Historical Tickets
            history_expander = st.expander("📜 Similar Historical Tickets", expanded=False)
            with history_expander:
                historical_tickets = [
                    {"id": "INC-987", "type": "Password Reset", "resolution": "Reset via AD, Okta sync issue fixed", "similarity": "95%"},
                    {"id": "INC-876", "type": "VPN Issue", "resolution": "Updated VPN client, network settings optimized", "similarity": "60%"},
                ]
                
                for hist_ticket in historical_tickets:
                    st.markdown(f"- **{hist_ticket['id']}** ({hist_ticket['similarity']} similar): {hist_ticket['type']} - {hist_ticket['resolution']}")
            
            # Diagnosis & Resolution
            diagnosis_expander = st.expander("🔧 Diagnosis & Resolution", expanded=False)
            with diagnosis_expander:
                if selected_ticket['type'] == "Password Reset":
                    st.markdown("""
**Diagnosis:** User reported Okta password reset error. Historical data shows similar issue due to AD-Okta sync delay.

**Recommended Resolution:**
1. Verify user account in Active Directory
2. Force sync between AD and Okta
3. Guide user through reset process
4. If issue persists, escalate to Identity Management team
                    """)
                elif selected_ticket['type'] == "VPN Issue":
                    st.markdown("""
**Diagnosis:** VPN connection drops indicate potential network instability or outdated client.

**Recommended Resolution:**
1. Check user's internet connection stability
2. Update VPN client to latest version
3. Verify firewall settings
4. Collect diagnostic logs for further analysis
                    """)
                else:
                    st.markdown("""
**Diagnosis:** Software installation request requires verification of user permissions and software availability.

**Recommended Resolution:**
1. Verify user has proper installation permissions
2. Check if software is in approved software catalog
3. Guide user through installation process
4. If issues persist, schedule remote assistance
                    """)
            
            st.markdown("")
            
            # Diagnostic Tools section
            st.markdown("---")
            st.markdown("### 🔧 Diagnostic Tools")
            platform = st.selectbox("Select Platform", ["Windows", "macOS", "Linux"], key="platform_selector")
            generate_script = st.button("Generate Diagnostic Script", use_container_width=True)

            # Handle diagnostic script generation
            if generate_script:
                script = generate_diagnostic_script(platform)
                
                st.markdown(f"**Generated {platform} Diagnostic Script:**")
                st.code(script, language="powershell" if platform == "Windows" else "bash")
                
                # Simulate log collection
                st.markdown("")
                st.markdown("**📋 Running diagnostic collection...**")
                time.sleep(1)
                
                # Simulate results
                st.markdown("**Diagnostic Results:**")
                diagnostic_result = f"Platform: {platform}\nStatus: Success\nCollected: System info, network status, event logs"
                st.code(diagnostic_result)
                
                # Update ticket with diagnostic data
                st.markdown(f"✅ **Diagnostic results attached to {selected_ticket['id']}**")
    else:
        history = st.session_state.history.get(ASSISTANT_ID, [])
        if not history or len(history) == 0:
            st.info("👈 Select a ticket from the left sidebar to begin analysis.")

# Render historical messages
for msg in st.session_state.history.get(ASSISTANT_ID, []):
    reasoning_contents, message_contents = _create_message_box(
        msg["role"], msg.get("name")
    )

    if "think" in msg and msg["think"]:
        reasoning_expander = reasoning_contents.expander("Reasoning", expanded=False)
        reasoning_expander.markdown(msg["think"])

    if msg.get("content"):
        message_contents.markdown(msg["content"])
    
    # Display ticket details if available
    if msg.get("ticket_details"):
        ticket = msg["ticket_details"]
        ticket_logs = f"**Ticket Details:**\n\n"
        ticket_logs += f"- **Ticket ID:** {ticket['ticket_id']}\n"
        ticket_logs += f"- **Issue Type:** {ticket['issue_type']}\n"
        ticket_logs += f"- **Priority:** {ticket['priority']}\n"
        ticket_logs += f"- **Status:** {ticket['status']}\n"
        ticket_logs += f"- **Assigned Group:** {ticket['assigned_group']}\n"
        ticket_logs += f"- **Created At:** {ticket['created_at']}\n"
        ticket_logs += f"- **Description:** {ticket['description']}"
        
        ticket_expander = message_contents.expander(f"ServiceNow Ticket {ticket['ticket_id']} created", expanded=True)
        ticket_expander.markdown(ticket_logs)

# ==============================================================================
# Handle User Input
# ==============================================================================

if USER_INPUT:
    _LOGGER.info(f"User input (thread: {THREAD_ID}): {USER_INPUT}")

    # Store last user input for ticket creation
    st.session_state.last_user_input = USER_INPUT
    
    # Reset closure confirmation flag
    st.session_state.show_closure_confirmation = False

    # Add user message to history
    st.session_state.history.setdefault(ASSISTANT_ID, []).append(
        {"role": "user", "content": USER_INPUT}
    )

    save_history(ASSISTANT_ID, THREAD_ID, st.session_state.history[ASSISTANT_ID], IS_ENGINEER)

    # Display user message
    with CHAT.chat_message("user"):
        st.markdown(USER_INPUT)

    # Initialize placeholders
    message_contents = None
    reasoning_contents = None
    accumulated_content = ""
    initial_history_length = len(st.session_state.history.get(ASSISTANT_ID, []))
    displayed_messages = set()
    
    for hist_msg in st.session_state.history.get(ASSISTANT_ID, []):
        hist_role = hist_msg.get("role") or hist_msg.get("type")
        hist_persona = hist_role
        if hist_role == "assistant":
            hist_persona = "ai"
        elif hist_role == "human":
            hist_persona = "user"
        hist_content = hist_msg.get("content", "")
        hist_name = hist_msg.get("name", "")
        hist_think = hist_msg.get("think", "") or hist_msg.get(
            "additional_kwargs", {}
        ).get("reasoning_content", "")
        think_snippet = hist_think[:100] if hist_think else ""
        msg_key = f"{hist_persona}_{hist_name}_{hist_content}_{think_snippet}"
        displayed_messages.add(msg_key)

    stream_mode = ["updates", "messages"] if STREAMING else ["updates", "values"]
    
    # Process AI response
    _LOGGER.info(f"[LLM] Request started - Thread: {THREAD_ID[:8]}, Input: {USER_INPUT[:50]}...")
    
    for msg in CLIENT.runs.stream(
        thread_id=THREAD_ID,
        assistant_id=ASSISTANT_ID,
        input={"messages": [{"role": "user", "content": USER_INPUT}]},
        stream_mode=stream_mode,
    ):
        event = msg.event.split("/")

        if "metadata" in event:
            continue

        data = msg.data

        # Handle non-streaming response
        if event[0] == "values":
            if not data.get("messages"):
                continue

            all_messages = data.get("messages")

            for idx, message in enumerate(all_messages):
                msg_type = message.get("type")
                msg_role = message.get("role")

                if msg_type == "human" or msg_role == "user":
                    persona = "user"
                elif msg_type == "ai" or msg_role == "assistant":
                    persona = "ai"
                elif msg_type == "tool" or msg_role == "tool":
                    persona = "tool"
                elif msg_role:
                    persona = msg_role
                else:
                    persona = "ai"

                msg_content = message.get("content", "")
                msg_name = message.get("name", "")

                # Log tool calls
                if persona == "tool":
                    _LOGGER.info(f"[TOOL] {msg_name}: {msg_content[:50]}...")

                if persona == "user":
                    continue

                if idx < initial_history_length:
                    continue

                reasoning_content = message.get("think", "") or message.get(
                    "additional_kwargs", {}
                ).get("reasoning_content", "")

                think_snippet = reasoning_content[:100] if reasoning_content else ""
                msg_key = f"{persona}_{msg_name}_{msg_content}_{think_snippet}"

                if msg_key in displayed_messages:
                    continue

                displayed_messages.add(msg_key)

                content = message.get("content", "")

                if not content and not reasoning_content:
                    continue

                reasoning_contents, message_contents = _create_message_box(
                    persona, msg_name
                )

                if reasoning_content:
                    reasoning_expander = reasoning_contents.expander(
                        "Reasoning", expanded=False
                    )
                    reasoning_expander.markdown(reasoning_content)

                if content:
                    if persona == "tool":
                        message_contents.code(content, language="json")
                    else:
                        message_contents.markdown(content)

        # Handle streaming messages
        elif event[0] == "messages":
            persona = data[0].get("type", "ai")
            graph_node_name = data[0].get("name", "")

            if reasoning_contents is None or message_contents is None:
                reasoning_contents, message_contents = _create_streaming_message_box(
                    persona, graph_node_name
                )

            reasoning_content = (
                data[0].get("additional_kwargs", {}).get("reasoning_content", "")
            )
            if reasoning_content:
                reasoning_expander = reasoning_contents.expander(
                    "Reasoning",
                    expanded=True,
                )
                reasoning_expander.markdown(reasoning_content)

            content = data[0].get("content", "")
            if content:
                accumulated_content += content
                message_contents.markdown(accumulated_content)

        # Handle message completion
        elif event[0] == "updates":
            message_contents = None
            reasoning_contents = None
            accumulated_content = ""

            for tool_call in data.get("tools", {}).get("messages", []):
                tool_message = {
                    "role": "tool",
                    "content": tool_call["content"],
                    "name": tool_call["name"],
                }
                if STREAMING or not any(
                    m.get("role") == "tool"
                    and m.get("name") == tool_call["name"]
                    and m.get("content") == tool_call["content"]
                    for m in st.session_state.history.get(ASSISTANT_ID, [])
                ):
                    st.session_state.history[ASSISTANT_ID].append(tool_message)

            for agent_message in data.get("model", {}).get("messages", []):
                agent_message = {
                    "role": "ai",
                    "content": agent_message["content"],
                    "name": agent_message["name"],
                    "think": agent_message.get("additional_kwargs", {}).get(
                        "reasoning_content", ""
                    ),
                }
                if STREAMING or not any(
                    m.get("role") == "ai"
                    and m.get("content") == agent_message["content"]
                    and m.get("think") == agent_message["think"]
                    for m in st.session_state.history.get(ASSISTANT_ID, [])
                ):
                    st.session_state.history[ASSISTANT_ID].append(agent_message)

    # After AI response
    _LOGGER.info(f"[LLM] Request completed - History: {len(st.session_state.history.get(ASSISTANT_ID, []))} messages")
    
    # Save updated history
    save_history(ASSISTANT_ID, THREAD_ID, st.session_state.history[ASSISTANT_ID], IS_ENGINEER)
    
    # Show closure confirmation for employees after AI response
    if not IS_ENGINEER:
        st.session_state.show_closure_confirmation = True


# ==============================================================================
# Conversation Closure Confirmation (Employee view only)
# ==============================================================================
def handle_closure_action(action_type):
    """Handle closure button actions."""
    if action_type == "solved":
        message_content = "✅ Great! This conversation has been saved to the knowledge base for future reference."
        st.session_state.history[ASSISTANT_ID].append({
            "role": "ai",
            "content": message_content
        })
        save_history(ASSISTANT_ID, THREAD_ID, st.session_state.history[ASSISTANT_ID], False)
        st.session_state.last_action = None
        st.session_state.show_closure_confirmation = False
        st.rerun()
    
    elif action_type == "create_ticket":
        issue_summary = st.session_state.last_user_input[:100] if st.session_state.get("last_user_input") else "IT Support Request"
        ticket = create_ticket("IT Support Request", "user@nvidia.com")
        assign_result = assign_ticket(ticket["ticket_id"])
        
        ticket_content = f"✅ **ServiceNow Ticket #{ticket['ticket_id']} has been created successfully.**\n\n"
        ticket_content += f"**Status:** {ticket['status']}\n"
        ticket_content += f"**Assigned To:** {assign_result}\n"
        ticket_content += f"**Priority:** {ticket['priority']}\n"
        ticket_content += f"**You will receive a Slack notification shortly with ticket details.**"
        
        st.session_state.history[ASSISTANT_ID].append({
            "role": "ai",
            "content": ticket_content,
            "ticket_details": {
                "ticket_id": ticket["ticket_id"],
                "issue_type": ticket["issue_type"],
                "priority": ticket["priority"],
                "status": ticket["status"],
                "assigned_group": assign_result,
                "created_at": ticket["created_at"],
                "description": issue_summary
            }
        })
        save_history(ASSISTANT_ID, THREAD_ID, st.session_state.history[ASSISTANT_ID], False)
        st.session_state.last_action = None
        st.session_state.show_closure_confirmation = False
        st.rerun()


# Show closure confirmation after conversation ends (Employee view only)
if not IS_ENGINEER and st.session_state.get("show_closure_confirmation"):
    st.markdown("---")
    st.markdown("### 💡 Has your issue been resolved?")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("✅ Problem Solved", use_container_width=True, key="problem_solved_btn"):
            handle_closure_action("solved")
    
    with col2:
        if st.button("🎫 Create IT Support Ticket", use_container_width=True, key="create_ticket_btn"):
            handle_closure_action("create_ticket")