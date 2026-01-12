#!/bin/bash

# RenderInk 工具安装脚本
# 自动下载并安装 xiaohongshu-mcp 到 tools/ 目录

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TOOL_DIR="$PROJECT_DIR/tools/xiaohongshu-mcp"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}📦 RenderInk 工具安装脚本${NC}"
echo ""

# 创建工具目录
mkdir -p "$TOOL_DIR"

# 检测系统和架构
detect_platform() {
    OS=$(uname -s)
    ARCH=$(uname -m)

    case "$OS" in
        Darwin)
            if [ "$ARCH" = "arm64" ]; then
                BINARY="xiaohongshu-mcp-darwin-arm64"
                PLATFORM="macOS (Apple Silicon)"
            else
                BINARY="xiaohongshu-mcp-darwin-amd64"
                PLATFORM="macOS (Intel)"
            fi
            ;;
        Linux)
            if [ "$ARCH" = "aarch64" ]; then
                BINARY="xiaohongshu-mcp-linux-arm64"
                PLATFORM="Linux (ARM64)"
            else
                BINARY="xiaohongshu-mcp-linux-amd64"
                PLATFORM="Linux (AMD64)"
            fi
            ;;
        *)
            echo -e "${RED}❌ 不支持的操作系统: $OS${NC}"
            exit 1
            ;;
    esac

    echo -e "${GREEN}✓${NC} 检测到平台: $PLATFORM"
}

# 获取最新版本号
get_latest_version() {
    echo -e "${BLUE}→${NC} 获取最新版本..."

    # 尝试从 GitHub API 获取最新版本
    LATEST_VERSION=$(curl -s https://api.github.com/repos/xpzouying/xiaohongshu-mcp/releases/latest | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/')

    if [ -z "$LATEST_VERSION" ]; then
        echo -e "${YELLOW}⚠${NC} 无法获取最新版本，使用默认版本 v1.0.0"
        LATEST_VERSION="v1.0.0"
    else
        echo -e "${GREEN}✓${NC} 最新版本: $LATEST_VERSION"
    fi
}

# 下载二进制文件
download_binary() {
    DOWNLOAD_URL="https://github.com/xpzouying/xiaohongshu-mcp/releases/download/${LATEST_VERSION}/${BINARY}"
    TARGET_PATH="$TOOL_DIR/xiaohongshu-mcp"

    echo -e "${BLUE}→${NC} 下载 $BINARY..."
    echo "  URL: $DOWNLOAD_URL"

    # 检查是否已存在
    if [ -f "$TARGET_PATH" ]; then
        echo -e "${YELLOW}⚠${NC} 已存在 xiaohongshu-mcp，是否覆盖？(y/N)"
        read -r response
        if [ "$response" != "y" ] && [ "$response" != "Y" ]; then
            echo -e "${BLUE}ℹ${NC} 跳过下载"
            return
        fi
    fi

    # 下载
    if curl -L --fail --progress-bar "$DOWNLOAD_URL" -o "$TARGET_PATH"; then
        chmod +x "$TARGET_PATH"
        echo -e "${GREEN}✓${NC} 下载成功！"
    else
        echo -e "${RED}❌ 下载失败${NC}"
        echo ""
        echo -e "${YELLOW}提示：您可以手动下载：${NC}"
        echo "  1. 访问: https://github.com/xpzouying/xiaohongshu-mcp/releases"
        echo "  2. 下载 $BINARY"
        echo "  3. 重命名为 xiaohongshu-mcp 并放到: $TOOL_DIR/"
        echo "  4. 运行: chmod +x $TOOL_DIR/xiaohongshu-mcp"
        exit 1
    fi
}

# 验证安装
verify_installation() {
    echo -e "${BLUE}→${NC} 验证安装..."

    if [ -x "$TOOL_DIR/xiaohongshu-mcp" ]; then
        # 尝试获取版本信息
        VERSION_OUTPUT=$("$TOOL_DIR/xiaohongshu-mcp" --version 2>&1 || echo "")
        if [ -n "$VERSION_OUTPUT" ]; then
            echo -e "${GREEN}✓${NC} 安装成功: $VERSION_OUTPUT"
        else
            echo -e "${GREEN}✓${NC} 安装成功"
        fi
    else
        echo -e "${RED}❌ 安装验证失败${NC}"
        exit 1
    fi
}

# 创建配置文件
create_config() {
    CONFIG_FILE="$TOOL_DIR/config.json"

    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${BLUE}→${NC} 创建默认配置..."
        cat > "$CONFIG_FILE" << 'EOF'
{
  "port": 18060,
  "data_dir": "../data/xiaohongshu",
  "headless": false,
  "timeout": 30000
}
EOF
        echo -e "${GREEN}✓${NC} 配置文件已创建: $CONFIG_FILE"
    fi
}

# 主流程
main() {
    detect_platform
    get_latest_version
    download_binary
    verify_installation
    create_config

    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   ✅ xiaohongshu-mcp 安装成功！              ║${NC}"
    echo -e "${GREEN}╠═══════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC}  二进制文件: $TOOL_DIR/xiaohongshu-mcp"
    echo -e "${GREEN}║${NC}  配置文件: $TOOL_DIR/config.json"
    echo -e "${GREEN}╠═══════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC}  使用方式："
    echo -e "${GREEN}║${NC}    ./scripts/start-all.sh  # 一键启动所有服务"
    echo -e "${GREEN}╚═══════════════════════════════════════════════╝${NC}"
}

main
