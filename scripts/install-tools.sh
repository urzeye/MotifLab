#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TOOL_DIR="${XHS_MCP_TOOL_DIR:-$PROJECT_DIR/tools/xiaohongshu-mcp}"
TEMP_DIR="${TMPDIR:-/tmp}"

REPO="${XHS_MCP_REPO:-xpzouying/xiaohongshu-mcp}"

IS_WINDOWS=false
PLATFORM=""
ASSET_PATTERN=""
ASSET_NAME=""
DOWNLOAD_URL=""
TEMP_FILE=""
EXTRACT_DIR=""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_err() { echo -e "${RED}[ERROR]${NC} $*"; }

replace_file() {
  local src="$1"
  local dst="$2"
  if [ -e "$dst" ]; then
    rm -f "$dst" || {
      log_err "Cannot overwrite $dst. Please stop running xiaohongshu-mcp related processes and retry."
      exit 1
    }
  fi
  mv -f "$src" "$dst"
}

cleanup() {
  [ -n "$TEMP_FILE" ] && [ -f "$TEMP_FILE" ] && rm -f "$TEMP_FILE" || true
  [ -n "$EXTRACT_DIR" ] && [ -d "$EXTRACT_DIR" ] && rm -rf "$EXTRACT_DIR" || true
}
trap cleanup EXIT

detect_platform() {
  local os arch
  os="$(uname -s)"
  arch="$(uname -m)"

  case "$os" in
    Darwin)
      if [ "$arch" = "arm64" ]; then
        ASSET_PATTERN="xiaohongshu-mcp-darwin-arm64"
        PLATFORM="macOS (Apple Silicon)"
      else
        ASSET_PATTERN="xiaohongshu-mcp-darwin-amd64"
        PLATFORM="macOS (Intel)"
      fi
      ;;
    Linux)
      if [ "$arch" = "aarch64" ] || [ "$arch" = "arm64" ]; then
        ASSET_PATTERN="xiaohongshu-mcp-linux-arm64"
        PLATFORM="Linux (ARM64)"
      else
        ASSET_PATTERN="xiaohongshu-mcp-linux-amd64"
        PLATFORM="Linux (AMD64)"
      fi
      ;;
    MINGW*|MSYS*|CYGWIN*)
      IS_WINDOWS=true
      if [ "$arch" = "x86_64" ] || [ "$arch" = "amd64" ]; then
        ASSET_PATTERN="xiaohongshu-mcp-windows-amd64"
        PLATFORM="Windows (AMD64)"
      else
        log_err "Windows unsupported architecture: $arch"
        exit 1
      fi
      ;;
    *)
      log_err "Unsupported OS: $os"
      exit 1
      ;;
  esac

  log_ok "Detected platform: $PLATFORM"
}

extract_archive() {
  local archive_path="$1"
  EXTRACT_DIR="$TOOL_DIR/.tmp_extract"
  rm -rf "$EXTRACT_DIR"
  mkdir -p "$EXTRACT_DIR"

  if [[ "$ASSET_NAME" == *.zip ]]; then
    if command -v unzip >/dev/null 2>&1; then
      unzip -qo "$archive_path" -d "$EXTRACT_DIR"
    elif command -v python3 >/dev/null 2>&1; then
      python3 - "$archive_path" "$EXTRACT_DIR" <<'PY'
import sys
import zipfile

zip_path = sys.argv[1]
target_dir = sys.argv[2]
with zipfile.ZipFile(zip_path, "r") as zf:
    zf.extractall(target_dir)
PY
    elif command -v python >/dev/null 2>&1; then
      python - "$archive_path" "$EXTRACT_DIR" <<'PY'
import sys
import zipfile

zip_path = sys.argv[1]
target_dir = sys.argv[2]
with zipfile.ZipFile(zip_path, "r") as zf:
    zf.extractall(target_dir)
PY
    else
      log_err "Cannot extract zip package. Please install unzip or python/python3."
      exit 1
    fi
  else
    tar -xzf "$archive_path" -C "$EXTRACT_DIR"
  fi
}

install_binaries() {
  local mcp_src login_src

  if [ "$IS_WINDOWS" = true ]; then
    mcp_src="$(find "$EXTRACT_DIR" -type f -name "xiaohongshu-mcp*.exe" | head -1)"
    login_src="$(find "$EXTRACT_DIR" -type f -name "xiaohongshu-login*.exe" | head -1)"

    if [ -z "$mcp_src" ]; then
      log_err "Could not find xiaohongshu-mcp*.exe in extracted files."
      exit 1
    fi

    replace_file "$mcp_src" "$TOOL_DIR/xiaohongshu-mcp.exe"
    chmod +x "$TOOL_DIR/xiaohongshu-mcp.exe" >/dev/null 2>&1 || true

    if [ -n "$login_src" ]; then
      replace_file "$login_src" "$TOOL_DIR/xiaohongshu-login.exe"
      chmod +x "$TOOL_DIR/xiaohongshu-login.exe" >/dev/null 2>&1 || true
      log_ok "Installed xiaohongshu-login.exe"
    else
      log_warn "xiaohongshu-login*.exe not found in package (optional)."
    fi
  else
    mcp_src="$(find "$EXTRACT_DIR" -type f -name "xiaohongshu-mcp*" ! -name "*.exe" | head -1)"
    login_src="$(find "$EXTRACT_DIR" -type f -name "xiaohongshu-login*" ! -name "*.exe" | head -1)"

    if [ -z "$mcp_src" ]; then
      log_err "Could not find xiaohongshu-mcp binary in extracted files."
      exit 1
    fi

    replace_file "$mcp_src" "$TOOL_DIR/xiaohongshu-mcp"
    chmod +x "$TOOL_DIR/xiaohongshu-mcp"

    if [ -n "$login_src" ]; then
      replace_file "$login_src" "$TOOL_DIR/xiaohongshu-login"
      chmod +x "$TOOL_DIR/xiaohongshu-login"
      log_ok "Installed xiaohongshu-login"
    else
      log_warn "xiaohongshu-login not found in package (optional)."
    fi
  fi
}

download_and_install() {
  local candidates=()
  local candidate downloaded=false

  if [ "$IS_WINDOWS" = true ]; then
    candidates=("${ASSET_PATTERN}.zip" "${ASSET_PATTERN}.tar.gz")
  else
    candidates=("${ASSET_PATTERN}.tar.gz" "${ASSET_PATTERN}.zip")
  fi

  if [ -f "$TOOL_DIR/xiaohongshu-mcp" ] || [ -f "$TOOL_DIR/xiaohongshu-mcp.exe" ]; then
    if [ "${XHS_MCP_INSTALL_FORCE:-0}" = "1" ]; then
      log_info "Existing xiaohongshu-mcp detected. Force overwrite enabled."
    else
      log_warn "Existing xiaohongshu-mcp detected. Overwrite? (y/N)"
      read -r response
      if [ "$response" != "y" ] && [ "$response" != "Y" ]; then
        log_info "Skipped installation."
        return
      fi
    fi
  fi

  log_info "Downloading latest release asset..."
  for candidate in "${candidates[@]}"; do
    ASSET_NAME="$candidate"
    DOWNLOAD_URL="https://github.com/${REPO}/releases/latest/download/${ASSET_NAME}"
    TEMP_FILE="${TEMP_DIR%/}/${ASSET_NAME}"
    log_info "Trying asset: $ASSET_NAME"
    echo "  URL: $DOWNLOAD_URL"
    if curl -L --fail --retry 3 --retry-delay 2 --retry-all-errors --progress-bar "$DOWNLOAD_URL" -o "$TEMP_FILE"; then
      downloaded=true
      log_ok "Downloaded asset: $ASSET_NAME"
      break
    fi
    rm -f "$TEMP_FILE" || true
    TEMP_FILE=""
  done

  if [ "$downloaded" = false ]; then
    log_err "Download failed for all candidate assets."
    echo "  Tried assets:"
    for candidate in "${candidates[@]}"; do
      echo "    - $candidate"
    done
    echo "  Release page: https://github.com/${REPO}/releases"
    exit 1
  fi

  log_info "Extracting package..."
  extract_archive "$TEMP_FILE"
  install_binaries
  log_ok "Installed binaries to $TOOL_DIR"
}

verify_installation() {
  log_info "Verifying installation..."
  if [ "$IS_WINDOWS" = true ]; then
    if [ ! -f "$TOOL_DIR/xiaohongshu-mcp.exe" ]; then
      log_err "Verification failed: xiaohongshu-mcp.exe not found."
      exit 1
    fi
    "$TOOL_DIR/xiaohongshu-mcp.exe" --help >/dev/null 2>&1 || true
  else
    if [ ! -x "$TOOL_DIR/xiaohongshu-mcp" ]; then
      log_err "Verification failed: xiaohongshu-mcp not executable."
      exit 1
    fi
    "$TOOL_DIR/xiaohongshu-mcp" --help >/dev/null 2>&1 || true
  fi
  log_ok "Installation verified."
}

create_config() {
  local config_file data_dir_path
  config_file="$TOOL_DIR/config.json"
  data_dir_path="$PROJECT_DIR/data/xiaohongshu"

  if [ "$IS_WINDOWS" = true ] && command -v cygpath >/dev/null 2>&1; then
    data_dir_path="$(cygpath -w "$data_dir_path" | sed 's#\\#/#g')"
  fi

  if [ -f "$config_file" ]; then
    log_info "config.json already exists, keeping current config."
    return
  fi

  cat > "$config_file" <<EOF
{
  "port": 18060,
  "data_dir": "${data_dir_path}",
  "headless": false,
  "timeout": 30000
}
EOF
  log_ok "Created config: $config_file"
}

main() {
  echo -e "${BLUE}MotifLab tool installer${NC}"
  mkdir -p "$TOOL_DIR"

  detect_platform
  download_and_install
  verify_installation
  create_config

  echo
  log_ok "xiaohongshu-mcp installation completed."
  echo "  Binary dir: $TOOL_DIR"
  echo "  Config: $TOOL_DIR/config.json"
}

main "$@"
