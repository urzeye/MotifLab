#!/bin/bash

# MotifLab 工具安装脚本
# 自动下载并安装 xiaohongshu-mcp 到 tools/ 目录

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TOOL_DIR="$PROJECT_DIR/tools/xiaohongshu-mcp"
TEMP_DIR="${TMPDIR:-/tmp}"

IS_WINDOWS=false
ASSET_NAME=""
PLATFORM=""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}📦 MotifLab 工具安装脚本${NC}"
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
                ASSET_NAME="xiaohongshu-mcp-darwin-arm64.tar.gz"
                PLATFORM="macOS (Apple Silicon)"
            else
                ASSET_NAME="xiaohongshu-mcp-darwin-amd64.tar.gz"
                PLATFORM="macOS (Intel)"
            fi
            ;;
        Linux)
            if [ "$ARCH" = "aarch64" ]; then
                ASSET_NAME="xiaohongshu-mcp-linux-arm64.tar.gz"
                PLATFORM="Linux (ARM64)"
            else
                ASSET_NAME="xiaohongshu-mcp-linux-amd64.tar.gz"
                PLATFORM="Linux (AMD64)"
            fi
            ;;
        MINGW*|MSYS*|CYGWIN*)
            IS_WINDOWS=true
            if [ "$ARCH" = "x86_64" ] || [ "$ARCH" = "amd64" ]; then
                ASSET_NAME="xiaohongshu-mcp-windows-amd64.zip"
                PLATFORM="Windows (AMD64)"
            else
                echo -e "${RED}❌ Windows 暂不支持当前架构: $ARCH${NC}"
                echo -e "${YELLOW}提示：目前官方仅提供 windows-amd64 版本${NC}"
                exit 1
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

# 解压下载包（支持 tar.gz / zip）
extract_archive() {
    TEMP_FILE="$1"
    EXTRACT_DIR="$TOOL_DIR/.tmp_extract"

    rm -rf "$EXTRACT_DIR"
    mkdir -p "$EXTRACT_DIR"

    if [[ "$ASSET_NAME" == *.zip ]]; then
        if command -v unzip >/dev/null 2>&1; then
            unzip -qo "$TEMP_FILE" -d "$EXTRACT_DIR"
        elif command -v python3 >/dev/null 2>&1; then
            python3 - "$TEMP_FILE" "$EXTRACT_DIR" <<'PY'
import sys
import zipfile

zip_path = sys.argv[1]
extract_dir = sys.argv[2]
with zipfile.ZipFile(zip_path, "r") as zf:
    zf.extractall(extract_dir)
PY
        elif tar -tf "$TEMP_FILE" >/dev/null 2>&1; then
            tar -xf "$TEMP_FILE" -C "$EXTRACT_DIR"
        else
            echo -e "${RED}❌ 无法解压 zip：请安装 unzip 或 python3${NC}"
            exit 1
        fi
    else
        tar -xzf "$TEMP_FILE" -C "$EXTRACT_DIR"
    fi
}

# 安装主程序与登录工具
install_binaries() {
    EXTRACT_DIR="$TOOL_DIR/.tmp_extract"
    MCP_SRC=""
    LOGIN_SRC=""

    if [ "$IS_WINDOWS" = true ]; then
        MCP_SRC=$(find "$EXTRACT_DIR" -type f -name "xiaohongshu-mcp*.exe" | head -1)
        LOGIN_SRC=$(find "$EXTRACT_DIR" -type f -name "xiaohongshu-login*.exe" | head -1)

        if [ -z "$MCP_SRC" ]; then
            echo -e "${RED}❌ 解压后未找到 xiaohongshu-mcp*.exe${NC}"
            ls -la "$EXTRACT_DIR"
            exit 1
        fi

        mv -f "$MCP_SRC" "$TOOL_DIR/xiaohongshu-mcp.exe"
        chmod +x "$TOOL_DIR/xiaohongshu-mcp.exe" >/dev/null 2>&1 || true

        cat > "$TOOL_DIR/xiaohongshu-mcp" << 'EOF'
#!/bin/bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$DIR/xiaohongshu-mcp.exe" "$@"
EOF
        chmod +x "$TOOL_DIR/xiaohongshu-mcp"

        if [ -n "$LOGIN_SRC" ]; then
            mv -f "$LOGIN_SRC" "$TOOL_DIR/xiaohongshu-login.exe"
            chmod +x "$TOOL_DIR/xiaohongshu-login.exe" >/dev/null 2>&1 || true
            cat > "$TOOL_DIR/xiaohongshu-login" << 'EOF'
#!/bin/bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$DIR/xiaohongshu-login.exe" "$@"
EOF
            chmod +x "$TOOL_DIR/xiaohongshu-login"
            echo -e "${GREEN}✓${NC} 登录工具已安装"
        else
            echo -e "${YELLOW}⚠${NC} 未找到登录工具 xiaohongshu-login*.exe（可忽略）"
        fi
    else
        MCP_SRC=$(find "$EXTRACT_DIR" -type f -name "xiaohongshu-mcp*" ! -name "*.exe" | head -1)
        LOGIN_SRC=$(find "$EXTRACT_DIR" -type f -name "xiaohongshu-login*" ! -name "*.exe" | head -1)

        if [ -z "$MCP_SRC" ]; then
            echo -e "${RED}❌ 解压后未找到 xiaohongshu-mcp 可执行文件${NC}"
            ls -la "$EXTRACT_DIR"
            exit 1
        fi

        mv -f "$MCP_SRC" "$TOOL_DIR/xiaohongshu-mcp"
        chmod +x "$TOOL_DIR/xiaohongshu-mcp"

        if [ -n "$LOGIN_SRC" ]; then
            mv -f "$LOGIN_SRC" "$TOOL_DIR/xiaohongshu-login"
            chmod +x "$TOOL_DIR/xiaohongshu-login"
            echo -e "${GREEN}✓${NC} 登录工具已安装"
        else
            echo -e "${YELLOW}⚠${NC} 未找到登录工具 xiaohongshu-login（可忽略）"
        fi
    fi
}

# 下载并安装二进制文件
download_binary() {
    DOWNLOAD_URL="https://github.com/xpzouying/xiaohongshu-mcp/releases/download/${LATEST_VERSION}/${ASSET_NAME}"
    TEMP_FILE="$TEMP_DIR/${ASSET_NAME}"

    echo -e "${BLUE}→${NC} 下载 $ASSET_NAME..."
    echo "  URL: $DOWNLOAD_URL"

    # 检查是否已存在
    if [ -f "$TOOL_DIR/xiaohongshu-mcp" ] || [ -f "$TOOL_DIR/xiaohongshu-mcp.exe" ]; then
        echo -e "${YELLOW}⚠${NC} 已存在 xiaohongshu-mcp，是否覆盖？(y/N)"
        read -r response
        if [ "$response" != "y" ] && [ "$response" != "Y" ]; then
            echo -e "${BLUE}ℹ${NC} 跳过下载"
            return
        fi
    fi

    # 下载压缩包（带重试）
    if curl -L --fail --retry 3 --retry-delay 2 --progress-bar "$DOWNLOAD_URL" -o "$TEMP_FILE"; then
        echo -e "${GREEN}✓${NC} 下载成功！"
        echo -e "${BLUE}→${NC} 解压文件..."
        extract_archive "$TEMP_FILE"
        install_binaries
        echo -e "${GREEN}✓${NC} 解压并安装完成！"

        # 清理临时文件
        rm -f "$TEMP_FILE"
        rm -rf "$TOOL_DIR/.tmp_extract"
    else
        echo -e "${RED}❌ 下载失败${NC}"
        echo ""
        echo -e "${YELLOW}提示：您可以手动下载：${NC}"
        echo "  1. 访问: https://github.com/xpzouying/xiaohongshu-mcp/releases"
        echo "  2. 下载 $ASSET_NAME"
        echo "  3. 解压并将 xiaohongshu-mcp 放到: $TOOL_DIR/"
        echo "  4. Linux/macOS: chmod +x $TOOL_DIR/xiaohongshu-mcp"
        exit 1
    fi
}

# 验证安装
verify_installation() {
    echo -e "${BLUE}→${NC} 验证安装..."

    if [ "$IS_WINDOWS" = true ]; then
        if [ -f "$TOOL_DIR/xiaohongshu-mcp.exe" ]; then
            if "$TOOL_DIR/xiaohongshu-mcp.exe" --help >/dev/null 2>&1; then
                echo -e "${GREEN}✓${NC} 安装成功！"
            else
                echo -e "${GREEN}✓${NC} 安装成功！"
            fi
        else
            echo -e "${RED}❌ 安装验证失败（未找到 xiaohongshu-mcp.exe）${NC}"
            exit 1
        fi
    else
        if [ -x "$TOOL_DIR/xiaohongshu-mcp" ]; then
            if "$TOOL_DIR/xiaohongshu-mcp" --help >/dev/null 2>&1; then
                echo -e "${GREEN}✓${NC} 安装成功！"
            else
                echo -e "${GREEN}✓${NC} 安装成功！"
            fi
        else
            echo -e "${RED}❌ 安装验证失败（未找到可执行文件）${NC}"
            exit 1
        fi
    fi
}

# 创建配置文件
create_config() {
    CONFIG_FILE="$TOOL_DIR/config.json"
    DATA_DIR_PATH="$PROJECT_DIR/data/xiaohongshu"

    if [ "$IS_WINDOWS" = true ] && command -v cygpath >/dev/null 2>&1; then
        DATA_DIR_PATH="$(cygpath -w "$DATA_DIR_PATH" | sed 's#\\#/#g')"
    fi

    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${BLUE}→${NC} 创建默认配置..."
        cat > "$CONFIG_FILE" << EOF
{
  "port": 18060,
  "data_dir": "${DATA_DIR_PATH}",
  "headless": false,
  "timeout": 30000
}
EOF
        echo -e "${GREEN}✓${NC} 配置文件已创建: $CONFIG_FILE"
    else
        echo -e "${BLUE}ℹ${NC} 已存在配置文件: $CONFIG_FILE（保持原配置不覆盖）"
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
    if [ "$IS_WINDOWS" = true ]; then
        echo -e "${GREEN}║${NC}    在 Git Bash 中执行: ./scripts/install-tools.sh"
        echo -e "${GREEN}║${NC}    或使用: scripts\\start-windows.bat"
    else
        echo -e "${GREEN}║${NC}    ./scripts/start-all.sh  # 一键启动所有服务"
    fi
    echo -e "${GREEN}╚═══════════════════════════════════════════════╝${NC}"
}

main
