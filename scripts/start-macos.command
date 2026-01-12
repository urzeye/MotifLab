#!/bin/bash

# RenderInk AI图文生成器 - macOS 启动脚本
# 双击此文件即可启动

set -e

# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

clear
echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════╗"
echo "║     🍎 RenderInk AI图文生成器 - macOS 版      ║"
echo "╚═══════════════════════════════════════════════╝"
echo -e "${NC}"

# 检查 Homebrew
check_homebrew() {
    if ! command -v brew &> /dev/null; then
        echo -e "${YELLOW}⚠️  未检测到 Homebrew，建议安装以获得更好体验${NC}"
        echo -e "   安装命令: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo ""
    fi
}

# 检查并安装依赖
check_requirements() {
    echo -e "${BLUE}📋 检查环境依赖...${NC}"
    echo ""

    # Python
    if command -v python3 &> /dev/null; then
        PYTHON_VER=$(python3 --version 2>&1)
        echo -e "  ${GREEN}✓${NC} $PYTHON_VER"
    else
        echo -e "  ${RED}✗${NC} Python3 未安装"
        echo -e "    ${YELLOW}请运行: brew install python3${NC}"
        exit 1
    fi

    # uv (推荐)
    if command -v uv &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} uv $(uv --version 2>&1 | head -1)"
        USE_UV=true
    else
        echo -e "  ${YELLOW}!${NC} uv 未安装 (推荐安装: curl -LsSf https://astral.sh/uv/install.sh | sh)"
        USE_UV=false
    fi

    # Node.js & pnpm
    if command -v pnpm &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} pnpm $(pnpm --version)"
        PKG_MANAGER="pnpm"
    elif command -v npm &> /dev/null; then
        echo -e "  ${YELLOW}!${NC} npm $(npm --version) (建议安装 pnpm: npm i -g pnpm)"
        PKG_MANAGER="npm"
    else
        echo -e "  ${RED}✗${NC} Node.js 未安装"
        echo -e "    ${YELLOW}请运行: brew install node${NC}"
        exit 1
    fi

    echo ""
}

# 安装项目依赖
install_deps() {
    echo -e "${BLUE}📦 安装项目依赖...${NC}"

    # 后端
    if [ "$USE_UV" = true ]; then
        echo -e "  ${CYAN}→${NC} 后端依赖 (uv)"
        uv sync --quiet 2>/dev/null || uv sync
    else
        echo -e "  ${CYAN}→${NC} 后端依赖 (pip)"
        pip3 install -e . --quiet 2>/dev/null || pip3 install -e .
    fi
    echo -e "  ${GREEN}✓${NC} 后端依赖完成"

    # 前端
    echo -e "  ${CYAN}→${NC} 前端依赖"
    cd frontend
    if [ ! -d "node_modules" ]; then
        $PKG_MANAGER install
    fi
    echo -e "  ${GREEN}✓${NC} 前端依赖完成"
    cd ..
    echo ""
}

# 清理
cleanup() {
    echo ""
    echo -e "${YELLOW}⏹  正在停止服务...${NC}"
    [ -n "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null
    [ -n "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null
    echo -e "${GREEN}✓${NC} 服务已停止，再见！"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 启动服务
start_services() {
    echo -e "${GREEN}🚀 启动服务...${NC}"
    echo ""

    # 后端
    if [ "$USE_UV" = true ]; then
        uv run python backend/app.py 2>&1 | sed 's/^/  [后端] /' &
    else
        python3 backend/app.py 2>&1 | sed 's/^/  [后端] /' &
    fi
    BACKEND_PID=$!
    sleep 2

    # 前端
    cd frontend
    $PKG_MANAGER run dev 2>&1 | sed 's/^/  [前端] /' &
    FRONTEND_PID=$!
    cd ..

    sleep 3
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║         🎉 服务启动成功！                     ║${NC}"
    echo -e "${GREEN}╠═══════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC}  🌐 前端: ${BLUE}http://localhost:5173${NC}              ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  🔧 后端: ${BLUE}http://localhost:12398${NC}             ${GREEN}║${NC}"
    echo -e "${GREEN}╠═══════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC}  按 ${YELLOW}Ctrl+C${NC} 或 ${YELLOW}Command+C${NC} 停止服务        ${GREEN}║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════╝${NC}"
    echo ""

    # 自动打开浏览器
    sleep 1
    open "http://localhost:5173" 2>/dev/null || true

    wait
}

# 主流程
check_homebrew
check_requirements
install_deps
start_services
