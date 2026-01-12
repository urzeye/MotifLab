#!/bin/bash

# RenderInk 一键启动脚本
# 启动所有服务：xiaohongshu-mcp + 后端 + 前端

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$PROJECT_DIR/data/xiaohongshu"
TOOL_DIR="$PROJECT_DIR/tools/xiaohongshu-mcp"
PID_FILE="$PROJECT_DIR/.service-pids"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

cd "$PROJECT_DIR"

clear
echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════╗"
echo "║     🚀 RenderInk 一键启动                     ║"
echo "╚═══════════════════════════════════════════════╝"
echo -e "${NC}"

# 创建数据目录
mkdir -p "$DATA_DIR"

# 清理函数
cleanup() {
    echo ""
    echo -e "${YELLOW}⏹  正在停止所有服务...${NC}"

    if [ -f "$PID_FILE" ]; then
        while read -r pid; do
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null || true
            fi
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi

    # 额外清理
    [ -n "$MCP_PID" ] && kill $MCP_PID 2>/dev/null || true
    [ -n "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null || true
    [ -n "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null || true

    echo -e "${GREEN}✓${NC} 所有服务已停止"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 检查 xiaohongshu-mcp 是否已安装
check_mcp() {
    if [ ! -x "$TOOL_DIR/xiaohongshu-mcp" ]; then
        echo -e "${YELLOW}⚠${NC} xiaohongshu-mcp 未安装"
        echo -e "${BLUE}→${NC} 正在自动安装..."
        "$SCRIPT_DIR/install-tools.sh"
    fi
}

# 检查 MCP 是否已运行
check_mcp_running() {
    if curl -s http://localhost:18060/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} xiaohongshu-mcp 已在运行 (端口 18060)"
        return 0
    fi
    return 1
}

# 启动 xiaohongshu-mcp
start_mcp() {
    echo -e "${BLUE}📦 启动 xiaohongshu-mcp...${NC}"

    if check_mcp_running; then
        return
    fi

    check_mcp

    # 启动 MCP 服务
    "$TOOL_DIR/xiaohongshu-mcp" \
        --port=18060 \
        --data-dir="$DATA_DIR" \
        > "$PROJECT_DIR/logs/mcp.log" 2>&1 &
    MCP_PID=$!
    echo "$MCP_PID" >> "$PID_FILE"

    # 等待服务启动
    echo -e "  等待 MCP 服务启动..."
    for i in {1..30}; do
        if check_mcp_running; then
            echo -e "  ${GREEN}✓${NC} MCP 服务已启动 (PID: $MCP_PID)"
            return
        fi
        sleep 1
    done

    echo -e "  ${YELLOW}⚠${NC} MCP 服务启动超时，请检查日志: $PROJECT_DIR/logs/mcp.log"
}

# 检查依赖
check_deps() {
    echo -e "${BLUE}📋 检查环境依赖...${NC}"

    # Python
    if command -v python3 &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} Python3 $(python3 --version 2>&1 | awk '{print $2}')"
    else
        echo -e "  ${RED}✗${NC} Python3 未安装"
        exit 1
    fi

    # uv
    if command -v uv &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} uv $(uv --version 2>&1 | head -1)"
        USE_UV=true
    else
        echo -e "  ${YELLOW}!${NC} uv 未安装"
        USE_UV=false
    fi

    # Node.js
    if command -v pnpm &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} pnpm $(pnpm --version)"
        PKG_MANAGER="pnpm"
    elif command -v npm &> /dev/null; then
        echo -e "  ${YELLOW}!${NC} npm $(npm --version)"
        PKG_MANAGER="npm"
    else
        echo -e "  ${RED}✗${NC} Node.js 未安装"
        exit 1
    fi

    echo ""
}

# 安装依赖
install_deps() {
    echo -e "${BLUE}📦 检查项目依赖...${NC}"

    # 后端
    if [ "$USE_UV" = true ]; then
        uv sync --quiet 2>/dev/null || uv sync
    else
        pip3 install -e . --quiet 2>/dev/null || pip3 install -e .
    fi
    echo -e "  ${GREEN}✓${NC} 后端依赖完成"

    # 前端
    cd frontend
    if [ ! -d "node_modules" ]; then
        $PKG_MANAGER install
    fi
    echo -e "  ${GREEN}✓${NC} 前端依赖完成"
    cd ..

    echo ""
}

# 启动后端
start_backend() {
    echo -e "${BLUE}🔧 启动后端服务...${NC}"

    mkdir -p "$PROJECT_DIR/logs"

    if [ "$USE_UV" = true ]; then
        uv run python backend/app.py > "$PROJECT_DIR/logs/backend.log" 2>&1 &
    else
        python3 backend/app.py > "$PROJECT_DIR/logs/backend.log" 2>&1 &
    fi
    BACKEND_PID=$!
    echo "$BACKEND_PID" >> "$PID_FILE"

    sleep 2
    echo -e "  ${GREEN}✓${NC} 后端已启动 (PID: $BACKEND_PID, 端口: 12398)"
}

# 启动前端
start_frontend() {
    echo -e "${BLUE}🎨 启动前端服务...${NC}"

    cd frontend
    $PKG_MANAGER run dev > "$PROJECT_DIR/logs/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    echo "$FRONTEND_PID" >> "$PID_FILE"
    cd ..

    sleep 3
    echo -e "  ${GREEN}✓${NC} 前端已启动 (PID: $FRONTEND_PID, 端口: 5173)"
}

# 显示启动信息
show_info() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║         🎉 所有服务启动成功！                 ║${NC}"
    echo -e "${GREEN}╠═══════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC}  🌐 前端:  ${BLUE}http://localhost:5173${NC}            ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  🔧 后端:  ${BLUE}http://localhost:12398${NC}           ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  📦 MCP:   ${BLUE}http://localhost:18060${NC}           ${GREEN}║${NC}"
    echo -e "${GREEN}╠═══════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC}  日志目录: ${CYAN}$PROJECT_DIR/logs/${NC}"
    echo -e "${GREEN}║${NC}  按 ${YELLOW}Ctrl+C${NC} 停止所有服务"
    echo -e "${GREEN}╚═══════════════════════════════════════════════╝${NC}"
    echo ""

    # 自动打开浏览器
    if command -v open &> /dev/null; then
        open "http://localhost:5173" 2>/dev/null || true
    elif command -v xdg-open &> /dev/null; then
        xdg-open "http://localhost:5173" 2>/dev/null &
    fi
}

# 主流程
main() {
    # 清理旧的 PID 文件
    rm -f "$PID_FILE"

    check_deps
    install_deps
    start_mcp
    start_backend
    start_frontend
    show_info

    # 保持运行
    wait
}

main
