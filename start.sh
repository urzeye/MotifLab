#!/bin/bash

# MotifLab - 启动脚本

set -e
cd "$(dirname "${BASH_SOURCE[0]}")"

# 颜色
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🚀 MotifLab${NC}"
echo ""

# 检查依赖
command -v python3 &>/dev/null || { echo "❌ 需要 Python3"; exit 1; }
command -v npm &>/dev/null || { echo "❌ 需要 Node.js"; exit 1; }

# 安装依赖（不安装为包，保持可编辑）
echo "📦 检查依赖..."
pip3 install -q -r requirements.txt 2>/dev/null || true
cd frontend && npm install --silent 2>/dev/null && cd ..

# 清理函数
cleanup() {
    echo -e "\n${YELLOW}⏹ 停止服务...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

# 启动服务
echo "🔧 启动后端..."
PYTHONPATH="$(pwd):$PYTHONPATH" python3 backend/app.py &
BACKEND_PID=$!
sleep 2

echo "🌐 启动前端..."
cd frontend && npm run dev &
FRONTEND_PID=$!
cd ..

sleep 3
echo ""
echo -e "${GREEN}✅ 启动成功！${NC}"
echo -e "   前端: ${BLUE}http://localhost:5173${NC}"
echo -e "   后端: ${BLUE}http://localhost:12398${NC}"
echo -e "   按 Ctrl+C 停止"
echo ""

# 打开浏览器
open "http://localhost:5173" 2>/dev/null || true

wait
