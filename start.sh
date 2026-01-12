#!/bin/bash

# RenderInk AI图文生成器 - 快捷启动脚本
# 自动检测系统并运行对应平台脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$(uname -s)" in
    Darwin)
        exec "$SCRIPT_DIR/scripts/start-macos.command"
        ;;
    Linux)
        exec "$SCRIPT_DIR/scripts/start-linux.sh"
        ;;
    *)
        echo "未知系统，请手动运行 scripts/ 目录下对应的启动脚本"
        exit 1
        ;;
esac
