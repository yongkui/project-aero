#!/bin/bash

# Project AERO - Startup Script
# This script starts both the backend and frontend services

set -e

echo "==================================="
echo "  Project AERO - Startup Script"
echo "==================================="
echo ""

# Check if conda environment is activated
if [[ -z "${CONDA_DEFAULT_ENV}" ]]; then
    echo "⚠️  Warning: Conda environment not activated"
    echo "   Trying to activate proj-aero environment..."
    eval "$(conda shell.bash hook)"
    conda activate proj-aero
    if [[ $? -ne 0 ]]; then
        echo "❌ Failed to activate conda environment"
        echo "   Please run: bash setup_env.sh"
        exit 1
    fi
    echo "✅ Activated conda environment: ${CONDA_DEFAULT_ENV}"
    echo ""
fi

# Export environment variables from .env if it exists
if [[ -f .env ]]; then
    while IFS= read -r line; do
        if [[ ! "$line" =~ ^# && -n "$line" ]]; then
            export "$line"
        fi
    done < .env
fi

# Check for required environment variables
if [[ -z "${NVIDIA_API_KEY}" ]]; then
    echo "❌ ERROR: NVIDIA_API_KEY environment variable not set"
    echo "   Please create a .env file with your API keys"
    exit 1
fi

if [[ -z "${TAVILY_API_KEY}" ]]; then
    echo "❌ ERROR: TAVILY_API_KEY environment variable not set"
    echo "   Please create a .env file with your API keys"
    exit 1
fi

echo "🚀 Starting Project AERO..."
echo ""

# Create storage directories if they don't exist
mkdir -p storage/logs storage/chat_history/employee storage/chat_history/engineer

# Start backend in background
echo "📡 Starting backend server..."
cd code/backend
export PYTHONPATH=$(pwd):$PYTHONPATH
nohup langgraph dev > ../../storage/logs/backend_startup.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started with PID: ${BACKEND_PID}"
cd ../..

# Wait for backend to start
echo ""
echo "⏳ Waiting for backend to initialize..."
sleep 5

# Check if backend is running
if ! curl -s http://127.0.0.1:2024/ok > /dev/null 2>&1; then
    echo "❌ Backend failed to start"
    echo "   Check logs: storage/logs/backend_startup.log"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi
echo "✅ Backend is ready at http://127.0.0.1:2024"

# Start frontend
echo ""
echo "🌐 Starting frontend application..."

# Start streamlit
streamlit run code/frontend/app.py --server.port 8501

# Cleanup on exit
trap "echo 'Stopping services...'; kill $BACKEND_PID 2>/dev/null || true" EXIT