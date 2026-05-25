#!/bin/bash

# proj-aero Environment Setup Script
# Usage: bash setup_env.sh

set -e  # Exit immediately on error

ENV_NAME="proj-aero"
PYTHON_VERSION="3.11"

echo "==================================="
echo "  proj-aero Environment Setup"
echo "==================================="
echo ""

# 1. Create conda environment (if not exists)
echo "📦 [1/6] Creating conda environment..."
if conda env list | grep -q "^${ENV_NAME} "; then
    echo "✅ Environment '${ENV_NAME}' already exists, skipping"
else
    echo "⏳ Creating new environment '${ENV_NAME}' (Python ${PYTHON_VERSION})..."
    conda create -n ${ENV_NAME} python=${PYTHON_VERSION} -y
    echo "✅ Environment '${ENV_NAME}' created successfully"
fi
echo ""

# 2. Activate conda environment
echo "🔄 [2/6] Activating conda environment..."
eval "$(conda shell.bash hook)"
conda activate ${ENV_NAME}
echo "✅ Environment '${ENV_NAME}' activated"
echo ""

# 3. Upgrade pip
echo "⬆️  [3/6] Upgrading pip..."
pip install --upgrade pip
echo "✅ pip upgraded successfully"
echo ""

# 4. Install Python dependencies
echo "📚 [4/6] Installing Python dependencies..."
pip install -r requirements.txt
echo "✅ Python dependencies installed successfully"
echo ""

# 5. Install nodejs/npm/npx
echo "🟢 [5/6] Installing nodejs/npm/npx..."
if command -v node &> /dev/null; then
    echo "✅ nodejs already installed, skipping"
else
    conda install -c conda-forge nodejs -y
    echo "✅ nodejs/npm/npx installed successfully"
fi
echo ""

# 6. Verify installation
echo "✅ [6/6] Verifying installation..."
echo "  Python: $(python --version)"
echo "  pip: $(pip --version)"
echo "  node: $(node --version)"
echo "  npm: $(npm --version)"
echo "  npx: $(npx --version)"
echo ""

echo "==================================="
echo "  ✅ Environment setup complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "  1. Activate environment: conda activate ${ENV_NAME}"
echo "  2. Start backend: cd code/backend && langgraph dev"
echo "  3. Start frontend: streamlit run code/frontend/app.py"
echo ""