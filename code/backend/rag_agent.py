"""
RAG Agent with MCP and Skills

Combines:
1. RAG - Knowledge base retrieval for IT help desk
2. MCP - Web search via Tavily for current information
3. Skills - Dynamic expertise loading for specialized tasks
"""

import logging
import os
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
load_dotenv(ENV_PATH)

# =============================================================================
# Logging Configuration
# =============================================================================
LOG_DIR = PROJECT_ROOT / "storage" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            LOG_DIR / f"backend_{datetime.now().strftime('%Y%m%d')}.log",
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)

_LOGGER = logging.getLogger(__name__)

_LOGGER.info(f"APP_PATH: {APP_PATH}")
_LOGGER.info(f"PROJECT_ROOT: {PROJECT_ROOT}")
_LOGGER.info(f"ENV_PATH: {ENV_PATH}")
_LOGGER.info(f"LOG_DIR: {LOG_DIR}")

# =============================================================================
# Configuration
# =============================================================================
DATA_DIR = PROJECT_ROOT / "data" / "it-kb-articles"
SKILLS_DIR = PROJECT_ROOT / "skills"
_LOGGER.info(f"DATA_DIR: {DATA_DIR}")
_LOGGER.info(f"SKILLS_DIR: {SKILLS_DIR}")

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120

LLM_MODEL = "nvidia/nemotron-3-super-120b-a12b"
RETRIEVER_RERANK_MODEL = "nvidia/llama-nemotron-rerank-1b-v2"
RETRIEVER_EMBEDDING_MODEL = "nvidia/llama-nemotron-embed-1b-v2"

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")

# =============================================================================
# Part 1: RAG - Knowledge Base Retrieval
# =============================================================================
_LOGGER.info(f"Reading knowledge base data from {DATA_DIR}")
data_loader = DirectoryLoader(
    DATA_DIR,
    glob="**/*",
    loader_cls=TextLoader,
    show_progress=True,
)
docs = data_loader.load()

_LOGGER.info(f"Ingesting {len(docs)} documents into FAISS vector database.")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
)
chunks = splitter.split_documents(docs)

embeddings = NVIDIAEmbeddings(
    model=RETRIEVER_EMBEDDING_MODEL,
    truncate="END",
    api_key=os.environ.get("NVIDIA_API_KEY"),
)

vectordb = FAISS.from_documents(chunks, embeddings)

kb_retriever = vectordb.as_retriever(search_type="similarity", search_kwargs={"k": 6})

reranker = NVIDIARerank(
    model=RETRIEVER_RERANK_MODEL, api_key=os.environ.get("NVIDIA_API_KEY")
)

RETRIEVER = ContextualCompressionRetriever(
    base_retriever=kb_retriever,
    base_compressor=reranker,
)

RETRIEVER_TOOL = create_retriever_tool(
    retriever=RETRIEVER,
    name="company_llc_it_knowledge_base",
    description=(
        "Search the internal IT knowledge base for Company LLC IT related questions and policies."
    ),
)

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
# Agent Setup
# =============================================================================
llm = ChatNVIDIA(model=LLM_MODEL, temperature=0.6, max_tokens=4096)

SYSTEM_PROMPT = """You are an IT help desk support agent with enhanced capabilities.

## Your Tools

1. **company_llc_it_knowledge_base** - Search internal IT, software, or company policies and procedures
   - Use for: Password resets, errors, request/access issues, technology or software issues (VPN/HPC/VM/email), company policies, etc.
   - Cite with [KB]

2. **web_search** - Search the web for current information
   - Use for: Questions beyond internal policies, current events, external resources
   - Cite with [Web]

3. **list_available_skills** - See what specialized skills you can load
   - Use when: User needs help with a specialized task

4. **get_skill** - Load a skill to gain expertise
   - Use when: You need specialized instructions (e.g., code review, technical writing)

## Guidelines

- Try the knowledge base FIRST for company-related or IT-related questions or issues
- Use web search when KB doesn't have the answer or for current information
- Load skills when doing specialized tasks
- Always cite your sources: [KB] for knowledge base, [Web] for web results
- Be concise and helpful
"""

AGENT = create_agent(
    model=llm,
    tools=[RETRIEVER_TOOL, web_search, get_skill, list_available_skills],
    system_prompt=SYSTEM_PROMPT,
)
