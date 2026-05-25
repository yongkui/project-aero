"""
Project AERO - RAG Agent with MCP and Skills

Combines:
1. RAG - Knowledge base retrieval for IT help desk
2. MCP - Web search via Tavily for current information
3. Skills - Dynamic expertise loading for specialized tasks
4. Enterprise Services - Mock integrations for ServiceNow, Jira, Identity, and Observability
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from langchain_classic.tools.retriever import create_retriever_tool
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_nvidia_ai_endpoints import ChatNVIDIA, NVIDIAEmbeddings, NVIDIARerank

# =============================================================================
# Path Configuration
# =============================================================================
APP_PATH = Path(__file__).resolve()
PROJECT_ROOT = APP_PATH.parent.parent.parent

ENV_PATH = PROJECT_ROOT / ".env"

# =============================================================================
# Logging Configuration - Setup FIRST before any other imports
# =============================================================================
LOG_DIR = PROJECT_ROOT / "storage" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / f"backend_{datetime.now().strftime('%Y%m%d')}.log"

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.handlers.clear()

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

_LOGGER = logging.getLogger(__name__)

_LOGGER.info("=" * 60)
_LOGGER.info("AERO Backend Starting...")
_LOGGER.info(f"Timestamp: {datetime.now().isoformat()}")
_LOGGER.info("=" * 60)
_LOGGER.info(f"APP_PATH: {APP_PATH}")
_LOGGER.info(f"PROJECT_ROOT: {PROJECT_ROOT}")
_LOGGER.info(f"ENV_PATH: {ENV_PATH}")
_LOGGER.info(f"LOG_DIR: {LOG_DIR}")
_LOGGER.info(f"LOG_FILE: {LOG_FILE}")

# Import enterprise services
from services import (
    create_ticket,
    close_ticket,
    assign_ticket,
    create_engineering_task,
    verify_user_identity,
    reset_ad_password,
    get_device_network_status,
)

_LOGGER.info("Loading environment variables...")
load_dotenv(ENV_PATH)
_LOGGER.info("Environment variables loaded successfully")

# =============================================================================
# Configuration
# =============================================================================
DATA_DIR = PROJECT_ROOT / "data" / "it-kb-articles"
SKILLS_DIR = PROJECT_ROOT / "skills"
_LOGGER.info(f"DATA_DIR: {DATA_DIR}")
_LOGGER.info(f"SKILLS_DIR: {SKILLS_DIR}")

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
_LOGGER.info(f"Text Splitter - Chunk Size: {CHUNK_SIZE}, Overlap: {CHUNK_OVERLAP}")

LLM_MODEL = "nvidia/nemotron-3-super-120b-a12b"
RETRIEVER_RERANK_MODEL = "nvidia/llama-nemotron-rerank-1b-v2"
RETRIEVER_EMBEDDING_MODEL = "nvidia/llama-nemotron-embed-1b-v2"
_LOGGER.info(f"LLM Model: {LLM_MODEL}")
_LOGGER.info(f"Embedding Model: {RETRIEVER_EMBEDDING_MODEL}")
_LOGGER.info(f"Rerank Model: {RETRIEVER_RERANK_MODEL}")

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
nvidia_api_key_set = "SET" if os.environ.get("NVIDIA_API_KEY") else "NOT SET"
_LOGGER.info(f"NVIDIA_API_KEY: {nvidia_api_key_set}")
_LOGGER.info(f"TAVILY_API_KEY: {'SET' if TAVILY_API_KEY else 'NOT SET'}")

# =============================================================================
# Part 1: RAG - Knowledge Base Retrieval
# =============================================================================
_LOGGER.info("=" * 60)
_LOGGER.info("Initializing RAG - Knowledge Base Retrieval")
_LOGGER.info("=" * 60)
_LOGGER.info(f"Reading knowledge base data from {DATA_DIR}")
data_loader = DirectoryLoader(
    DATA_DIR,
    glob="**/*",
    loader_cls=TextLoader,
    show_progress=True,
)
docs = data_loader.load()
_LOGGER.info(f"Loaded {len(docs)} documents from knowledge base")

_LOGGER.info(f"Splitting documents into chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
)
chunks = splitter.split_documents(docs)
_LOGGER.info(f"Created {len(chunks)} document chunks")

_LOGGER.info(f"Initializing embeddings model: {RETRIEVER_EMBEDDING_MODEL}")
embeddings = NVIDIAEmbeddings(
    model=RETRIEVER_EMBEDDING_MODEL,
    truncate="END",
    api_key=os.environ.get("NVIDIA_API_KEY"),
)
_LOGGER.info("Embeddings model initialized successfully")

_LOGGER.info("Building FAISS vector database...")
vectordb = FAISS.from_documents(chunks, embeddings)
_LOGGER.info("FAISS vector database built successfully")

kb_retriever = vectordb.as_retriever(search_type="similarity", search_kwargs={"k": 6})
_LOGGER.info("Knowledge base retriever configured")

_LOGGER.info(f"Initializing rerank model: {RETRIEVER_RERANK_MODEL}")
reranker = NVIDIARerank(
    model=RETRIEVER_RERANK_MODEL, api_key=os.environ.get("NVIDIA_API_KEY")
)
_LOGGER.info("Rerank model initialized successfully")

RETRIEVER = ContextualCompressionRetriever(
    base_retriever=kb_retriever,
    base_compressor=reranker,
)
_LOGGER.info("Contextual compression retriever configured")

RETRIEVER_TOOL = create_retriever_tool(
    retriever=RETRIEVER,
    name="it_knowledge_base",
    description=(
        "Search the internal IT knowledge base for IT related questions, policies, procedures and troubleshooting guides."
    ),
)
_LOGGER.info("Knowledge base tool created: it_knowledge_base")

# =============================================================================
# Part 2: MCP - Web Search Tool
# =============================================================================
MCP_CONFIG = {
    "tavily": {
        "transport": "stdio",
        "command": "npx",
        "args": [
            "-y",
            "mcp-remote",
            f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}",
        ],
    }
}


@tool
async def web_search(query: str) -> str:
    """Search the web for current information on any topic.

    Use this when:
    - The knowledge base doesn't have the answer
    - User asks about current events or recent information
    - User needs information beyond internal IT policies
    """
    try:
        client = MultiServerMCPClient(MCP_CONFIG)
        async with client.session("tavily") as session:
            result = await session.call_tool("tavily_search", {"query": query})

            if result and result.content:
                return result.content[0].text
            return "No results found."
    except Exception as e:
        return f"Search failed: {str(e)}"


# =============================================================================
# Part 3: Skills - Dynamic Expertise Loading
# =============================================================================
def load_skill(skill_name: str) -> str:
    """Load a skill from the skills directory."""
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"
    if skill_path.exists():
        return skill_path.read_text()
    return f"Skill '{skill_name}' not found."


def list_skills() -> list[str]:
    """List all available skills."""
    if not SKILLS_DIR.exists():
        return []
    return [
        d.name for d in SKILLS_DIR.iterdir() if d.is_dir() and (d / "SKILL.md").exists()
    ]


@tool
def get_skill(skill_name: str) -> str:
    """Load a specific skill to gain expertise in that area.

    Available skills can be found using list_available_skills.
    Skills provide specialized instructions for tasks like code review,
    technical writing, etc.
    """
    return load_skill(skill_name)


@tool
def list_available_skills() -> list[str]:
    """List all available skills that can be loaded.

    Returns a list of skill names. Use get_skill(name) to load one.
    """
    return list_skills()


# =============================================================================
# Part 4: Enterprise Service Tools
# =============================================================================

@tool
def servicenow_create_ticket(issue_type: str, user_email: str) -> dict:
    """Create a ServiceNow ticket for IT support requests.

    Production: Replace with real ServiceNow REST API call.

    Args:
        issue_type: The type of issue (e.g., "Password Reset", "Hardware Issue")
        user_email: The email address of the user reporting the issue

    Returns:
        Ticket object with ID, status, and other details
    """
    return create_ticket(issue_type, user_email)


@tool
def servicenow_assign_ticket(ticket_id: str, group: str = "China L1 Support") -> str:
    """Assign a ServiceNow ticket to a support group.

    Production: Replace with real ServiceNow API.

    Args:
        ticket_id: The ID of the ticket to assign (e.g., "INC-1001")
        group: The support group to assign the ticket to

    Returns:
        Assignment confirmation message
    """
    return assign_ticket(ticket_id, group)


@tool
def servicenow_close_ticket(ticket_id: str, resolution: str) -> str:
    """Close a ServiceNow ticket with a resolution.

    Production: Replace with real ServiceNow API.

    Args:
        ticket_id: The ID of the ticket to close (e.g., "INC-1001")
        resolution: The resolution description

    Returns:
        Closure confirmation message
    """
    return close_ticket(ticket_id, resolution)


@tool
def jira_create_engineering_task(summary: str, priority: str = "Medium") -> dict:
    """Create an engineering task in Jira for escalation.

    Production: Replace with real Jira REST API call.

    Args:
        summary: The task summary/description
        priority: Task priority (Low, Medium, High, Critical)

    Returns:
        Jira task object with ID, key, status, and other details
    """
    return create_engineering_task(summary, priority)


@tool
def identity_verify_user(user_email: str) -> dict:
    """Verify user identity via Active Directory.

    Production: Replace with real Active Directory/LDAP API call.

    Args:
        user_email: The user's email address to verify

    Returns:
        Verification result with status and user details
    """
    return verify_user_identity(user_email)


@tool
def identity_reset_password(user_email: str) -> dict:
    """Reset user password via Okta API.

    Production: Replace with real Okta API call.

    Args:
        user_email: The user's email address

    Returns:
        Password reset result
    """
    return reset_ad_password(user_email)


@tool
def observability_get_network_status(device_id: str = "default") -> dict:
    """Get device network status from observability system.

    Production: Replace with real Grafana/Prometheus API call.

    Args:
        device_id: Optional device identifier to query

    Returns:
        Network status data with latency, throughput, and connection status
    """
    return get_device_network_status(device_id)


# =============================================================================
# Agent Setup
# =============================================================================

SYSTEM_PROMPT = """You are Project AERO, NVIDIA China IT Operations Agent - an IT help desk support agent with enhanced capabilities.

## Your Tools

1. **it_knowledge_base** - Search internal IT, software, or company policies and procedures
   - Use for: Password resets, errors, request/access issues, technology or software issues (VPN/HPC/VM/email), company policies, etc.
   - Cite with [KB]

2. **web_search** - Search the web for current information
   - Use for: Questions beyond internal policies, current events, external resources
   - Cite with [Web]

3. **list_available_skills** - See what specialized skills you can load
   - Use when: User needs help with a specialized task

4. **get_skill** - Load a skill to gain expertise
   - Use when: You need specialized instructions (e.g., code review, technical writing)

5. **servicenow_create_ticket** - Create ServiceNow IT support tickets
   - Use for: Logging IT incidents, service requests

6. **servicenow_assign_ticket** - Assign ServiceNow tickets to support groups
   - Use for: Routing tickets to appropriate support teams

7. **servicenow_close_ticket** - Close ServiceNow tickets with resolution
   - Use for: Completing ticket workflows

8. **jira_create_engineering_task** - Create Jira engineering tasks
   - Use for: Escalating issues to engineering teams

9. **identity_verify_user** - Verify user identity via Active Directory
   - Use for: Authentication and identity verification

10. **identity_reset_password** - Reset user password via Okta
    - Use for: Password reset requests

11. **observability_get_network_status** - Get device network status
    - Use for: Troubleshooting network connectivity issues

## Guidelines

- Try the knowledge base FIRST for company-related or IT-related questions or issues
- Use web search when KB doesn't have the answer or for current information
- Load skills when doing specialized tasks
- Use ServiceNow integration for ticket management
- Use identity tools for authentication and password management
- Always cite your sources: [KB] for knowledge base, [Web] for web results
- Be concise and helpful
"""

_LOGGER.info("=" * 60)
_LOGGER.info("Initializing AERO Agent")
_LOGGER.info("=" * 60)
_LOGGER.info(f"Initializing LLM: {LLM_MODEL}")
llm = ChatNVIDIA(model=LLM_MODEL, temperature=0.6, max_tokens=4096)
_LOGGER.info("LLM initialized successfully")

_LOGGER.info("Defining system prompt...")

AGENT = create_agent(
    model=llm,
    tools=[
        RETRIEVER_TOOL,
        web_search,
        get_skill,
        list_available_skills,
        servicenow_create_ticket,
        servicenow_assign_ticket,
        servicenow_close_ticket,
        jira_create_engineering_task,
        identity_verify_user,
        identity_reset_password,
        observability_get_network_status,
    ],
    system_prompt=SYSTEM_PROMPT,
)

_LOGGER.info("=" * 60)
_LOGGER.info("AERO Agent Initialization Complete!")
_LOGGER.info("=" * 60)
_LOGGER.info("Ready to accept requests...")
_LOGGER.info("Backend started successfully")