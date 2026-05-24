#!/bin/bash

# itechops 环境配置脚本
# 用法: bash setup_env.sh

set -e  # 遇到错误立即退出

ENV_NAME="itechops"
PYTHON_VERSION="3.11"

echo "==================================="
echo "  itechops 环境配置脚本"
echo "==================================="
echo ""

# 1. 创建 conda 环境（如果不存在）
echo "📦 [1/6] 创建 conda 环境..."
if conda env list | grep -q "^${ENV_NAME} "; then
    echo "✅ 环境 '${ENV_NAME}' 已存在，跳过创建"
else
    echo "⏳ 创建新环境 '${ENV_NAME}' (Python ${PYTHON_VERSION})..."
    conda create -n ${ENV_NAME} python=${PYTHON_VERSION} -y
    echo "✅ 环境 '${ENV_NAME}' 创建完成"
fi
echo ""

# 2. 激活 conda 环境
echo "🔄 [2/6] 激活 conda 环境..."
eval "$(conda shell.bash hook)"
conda activate ${ENV_NAME}
echo "✅ 环境 '${ENV_NAME}' 已激活"
echo ""

# 3. 升级 pip
echo "⬆️  [3/6] 升级 pip..."
pip install --upgrade pip
echo "✅ pip 升级完成"
echo ""

# 4. 安装 Python 依赖
echo "📚 [4/6] 安装 Python 依赖..."
pip install -r requirements.txt
echo "✅ Python 依赖安装完成"
echo ""

# 5. 安装 nodejs/npm/npx
echo "🟢 [5/6] 安装 nodejs/npm/npx..."
if command -v node &> /dev/null; then
    echo "✅ nodejs 已安装，跳过"
else
    conda install -c conda-forge nodejs -y
    echo "✅ nodejs/npm/npx 安装完成"
fi
echo ""

# 6. 验证安装
echo "✅ [6/6] 验证安装..."
echo "  Python: $(python --version)"
echo "  pip: $(pip --version)"
echo "  node: $(node --version)"
echo "  npm: $(npm --version)"
echo "  npx: $(npx --version)"
echo ""

echo "==================================="
echo "  ✅ 环境配置完成！"
echo "==================================="
echo ""
echo "下一步:"
echo "  1. 激活环境: conda activate ${ENV_NAME}"
echo "  2. 启动后端: cd code/backend && langgraph dev"
echo "  3. 启动前端: streamlit run code/frontend/app.py"
echo ""
