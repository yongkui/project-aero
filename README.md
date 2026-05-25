# Project AERO: AI-Enabled Regional Operations
## Internal Codename: itechops

IT Help Desk Assistant powered by RAG (Retrieval-Augmented Generation)

## 🎯 Overview

Project AERO is an intelligent IT support agent for NVIDIA China IT Operations that combines:
- **RAG** - Knowledge base retrieval for IT help desk
- **MCP** - Web search via Tavily for current information
- **Skills** - Dynamic expertise loading for specialized tasks
- **Enterprise Services** - Mock integrations for ServiceNow, Jira, Identity, and Observability

## 📁 Project Structure

```
itechops/
├── code/
│   ├── backend/           # LangGraph backend
│   │   ├── rag_agent.py   # RAG agent implementation
│   │   ├── mcp_server.py  # MCP server for web search
│   │   ├── services/      # Enterprise service mocks
│   │   │   ├── __init__.py
│   │   │   ├── servicenow.py
│   │   │   ├── jira.py
│   │   │   ├── identity.py
│   │   │   └── observability.py
│   │   └── langgraph.json
│   └── frontend/          # Streamlit frontend
│       └── app.py
├── data/
│   └── it-kb-articles/    # IT knowledge base articles
├── skills/                # Agent skills
│   ├── code_review/
│   └── technical_writing/
├── storage/               # Runtime storage (logs, chat history)
├── .env                   # Environment variables
├── requirements.txt       # Python dependencies
└── setup_env.sh          # Environment setup script
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Run the setup script
bash setup_env.sh

# Activate the environment
conda activate proj-aero
```

### 2. Configure Environment Variables

Create a `.env` file with your API keys:

```env
NVIDIA_API_KEY=your_nvidia_api_key
TAVILY_API_KEY=your_tavily_api_key
```

### 3. Start the Backend

```bash
cd code/backend
langgraph dev
```

Wait for: `Ready accept requests at http://127.0.0.1:2024`

### 4. Start the Frontend

In a new terminal:

```bash
streamlit run code/frontend/app.py
```

## 💡 Features

- **IT Knowledge Base**: Searches internal IT policies and procedures
- **Web Search**: Real-time information via Tavily MCP
- **Skills System**: Dynamic expertise loading for specialized tasks
- **Conversation History**: Persistent chat history across sessions
- **Reasoning Display**: View AI thinking process
- **ServiceNow Integration**: Automated ticket creation, assignment, and closure
- **Operations Dashboard**: IT operational metrics display
- **Diagnostic Tools**: Cross-platform diagnostic script generation

## 🏢 Enterprise Services

Project AERO integrates with the following enterprise services via mock implementations:

| Service | Description | Status |
|---------|-------------|--------|
| **ServiceNow** | IT service management, ticket creation and tracking | Mock |
| **Jira** | Engineering task management, escalation | Mock |
| **Identity** | Active Directory/Okta user verification and password reset | Mock |
| **Observability** | Grafana/Prometheus network status monitoring | Mock |

## 🛠️ Development

### Add New Skills

Create a new skill in `skills/<skill_name>/SKILL.md`

### Update Knowledge Base

Add markdown files to `data/it-kb-articles/`

### Add New Services

Add new mock services in `code/backend/services/`

### Environment Setup

See `setup_env.sh` for complete environment configuration

## 🌐 Access

- **Backend API**: http://127.0.0.1:2024
- **Frontend UI**: http://localhost:8501

## ℹ️ Note

All enterprise service integrations are mock implementations for demonstration purposes. In production, replace these with real API calls.