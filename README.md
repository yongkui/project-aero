# itechops

IT Help Desk Assistant powered by RAG (Retrieval-Augmented Generation)

## 🎯 Overview

itechops is an intelligent IT support agent that combines:
- **RAG** - Knowledge base retrieval for IT help desk
- **MCP** - Web search via Tavily for current information
- **Skills** - Dynamic expertise loading for specialized tasks

## 📁 Project Structure

```
itechops/
├── code/
│   ├── backend/           # LangGraph backend
│   │   ├── rag_agent.py  # RAG agent implementation
│   │   ├── mcp_server.py # MCP server for web search
│   │   └── langgraph.json
│   └── frontend/          # Streamlit frontend
│       └── app.py
├── data/
│   ├── it-kb-articles/  # IT knowledge base articles
│   └── evaluation/         # Test cases
├── skills/                 # Agent skills
│   ├── code_review/
│   └── technical_writing/
├── storage/                # Runtime storage (logs, chat history)
├── .env                    # Environment variables
├── requirements.txt       # Python dependencies
└── setup_env.sh          # Environment setup script
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Run the setup script
bash setup_env.sh

# Activate the environment
conda activate itechops
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

## 🛠️ Development

### Add New Skills

Create a new skill in `skills/<skill_name>/SKILL.md`

### Update Knowledge Base

Add markdown files to `data/it-kb-articles/`

### Environment Setup

See `setup_env.sh` for complete environment configuration

