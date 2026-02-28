"""
xiaohongshu-mcp process manager.

Responsibilities:
- check/start/stop mcp process
- expose status
- call mcp tools
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class MCPManager:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent

        # Windows must execute .exe; executing a bash wrapper can trigger WinError 193.
        default_binary_path = self.project_root / "tools" / "xiaohongshu-mcp" / "xiaohongshu-mcp"
        windows_binary_path = default_binary_path.with_suffix(".exe")
        if os.name == "nt":
            self.binary_path = windows_binary_path
        else:
            self.binary_path = default_binary_path

        self.data_dir = self.project_root / "data" / "xiaohongshu"
        self.logs_dir = self.project_root / "logs"
        self.install_script = self.project_root / "scripts" / "install-tools.sh"
        configured_mcp_url = os.getenv("XHS_MCP_URL") or os.getenv("MCP_URL")
        self.mcp_url = (configured_mcp_url or "http://127.0.0.1:18060").rstrip("/")
        self.mcp_endpoint = os.getenv("XHS_MCP_ENDPOINT", "/mcp")
        self.default_tool_timeout_seconds = self._read_timeout_env("XHS_MCP_TOOL_TIMEOUT", 60)
        self.publish_tool_timeout_seconds = self._read_timeout_env("XHS_MCP_PUBLISH_TIMEOUT", 300)
        if self.publish_tool_timeout_seconds < self.default_tool_timeout_seconds:
            self.publish_tool_timeout_seconds = self.default_tool_timeout_seconds

        self._session_id: Optional[str] = None
        self.process: Optional[subprocess.Popen] = None
        self._install_lock = threading.Lock()

    @staticmethod
    def _read_timeout_env(name: str, default: int) -> int:
        raw = str(os.getenv(name, str(default))).strip()
        try:
            value = int(raw)
            return max(5, value)
        except Exception:
            return max(5, int(default))

    def _get_tool_timeout_seconds(self, tool: str) -> int:
        if tool in {"publish_content", "publish_with_video"}:
            return self.publish_tool_timeout_seconds
        return self.default_tool_timeout_seconds

    def is_running(self) -> bool:
        try:
            resp = httpx.get(f"{self.mcp_url}/health", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False

    def start(self, timeout: int = 30) -> bool:
        if self.is_running():
            logger.info("MCP service already running")
            return True

        if not self.binary_path.exists():
            logger.error("xiaohongshu-mcp not installed, please run scripts/install-tools.sh")
            raise FileNotFoundError(
                f"xiaohongshu-mcp not installed.\n"
                f"Please run: ./scripts/install-tools.sh\n"
                f"Or place binary at: {self.binary_path}"
            )

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = self.logs_dir / "mcp.log"

        logger.info(f"Starting xiaohongshu-mcp: {self.binary_path}")
        try:
            with open(log_file, "a", encoding="utf-8", errors="ignore") as f:
                self.process = subprocess.Popen(
                    [
                        str(self.binary_path),
                        "-port=:18060",
                        "-headless=false",
                    ],
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    cwd=str(self.project_root),
                )

            for _ in range(timeout):
                time.sleep(1)
                if self.is_running():
                    logger.info(f"MCP service started (PID: {self.process.pid if self.process else 'N/A'})")
                    return True

            logger.error(f"MCP service start timeout ({timeout}s)")
            return False
        except Exception as exc:
            logger.error(f"Failed to start MCP service: {exc}")
            return False

    def stop(self):
        if not self.process:
            return
        try:
            self.process.terminate()
            self.process.wait(timeout=5)
            logger.info("MCP service stopped")
        except Exception as exc:
            logger.warning(f"Failed to stop MCP service gracefully: {exc}")
            self.process.kill()
        finally:
            self.process = None
            self._session_id = None

    def ensure_running(self) -> bool:
        if not self.is_running():
            self._session_id = None
            return self.start()
        return True

    @staticmethod
    def _tail_text(text: str, max_lines: int = 40) -> str:
        lines = [line.rstrip() for line in (text or "").splitlines() if line.strip()]
        return "\n".join(lines[-max_lines:])

    def _resolve_bash_executable(self) -> Optional[str]:
        candidates: list[str] = []
        env_bash = os.getenv("BASH_EXECUTABLE")
        if env_bash:
            candidates.append(env_bash)

        which_bash = shutil.which("bash")
        if which_bash:
            candidates.append(which_bash)

        if os.name == "nt":
            candidates.extend(
                [
                    "C:/Program Files/Git/bin/bash.exe",
                    "C:/Program Files/Git/usr/bin/bash.exe",
                ]
            )

        seen = set()
        for candidate in candidates:
            resolved = str(Path(candidate))
            if resolved in seen:
                continue
            seen.add(resolved)
            if Path(candidate).exists():
                return str(Path(candidate))
        return None

    def install_binary(self, timeout: int = 300) -> Dict[str, Any]:
        if not self._install_lock.acquire(blocking=False):
            return {
                "success": False,
                "code": "install_in_progress",
                "error": "已有安装任务在执行，请稍后重试。",
            }

        try:
            if self.binary_path.exists():
                return {
                    "success": True,
                    "message": "xiaohongshu-mcp 已安装。",
                    "already_installed": True,
                    "status": self.get_status(),
                }

            if not self.install_script.exists():
                return {
                    "success": False,
                    "error": f"安装脚本不存在: {self.install_script}",
                }

            bash_executable = self._resolve_bash_executable()
            if not bash_executable:
                return {
                    "success": False,
                    "error": "未找到 bash 可执行文件。请安装 Git Bash 或设置 BASH_EXECUTABLE 环境变量。",
                }

            env = os.environ.copy()
            env["XHS_MCP_INSTALL_FORCE"] = "1"

            logger.info(f"Installing xiaohongshu-mcp via script: {self.install_script}")
            completed = subprocess.run(
                [bash_executable, str(self.install_script)],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                env=env,
            )
            output = self._tail_text("\n".join(part for part in [completed.stdout, completed.stderr] if part))

            if completed.returncode != 0:
                logger.error(f"install-tools.sh failed with code {completed.returncode}")
                return {
                    "success": False,
                    "error": f"安装失败（退出码 {completed.returncode}）",
                    "output": output,
                }

            if not self.binary_path.exists():
                return {
                    "success": False,
                    "error": "安装命令执行完成，但未找到 xiaohongshu-mcp 可执行文件。",
                    "output": output,
                }

            return {
                "success": True,
                "message": "xiaohongshu-mcp 安装完成。",
                "output": output,
                "status": self.get_status(),
            }
        except subprocess.TimeoutExpired as exc:
            output = self._tail_text("\n".join(part for part in [(exc.stdout or ""), (exc.stderr or "")] if part))
            return {
                "success": False,
                "error": f"安装超时（>{timeout} 秒）",
                "output": output,
            }
        except Exception as exc:
            logger.error(f"Install xiaohongshu-mcp failed: {exc}")
            return {"success": False, "error": str(exc)}
        finally:
            self._install_lock.release()

    async def _mcp_initialize(self, client: httpx.AsyncClient):
        payload = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {
                    "name": "motiflab-backend",
                    "version": "0.1.0",
                },
            },
        }
        resp = await client.post(f"{self.mcp_url}{self.mcp_endpoint}", json=payload)
        resp.raise_for_status()

        session_id = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id")
        if not session_id:
            raise RuntimeError("MCP initialize succeeded but no Mcp-Session-Id returned")
        self._session_id = session_id

        # Complete initialize handshake.
        await client.post(
            f"{self.mcp_url}{self.mcp_endpoint}",
            headers={"Mcp-Session-Id": self._session_id},
            json={
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            },
        )

    @staticmethod
    def _extract_text_from_content(content: Any) -> str:
        if not isinstance(content, list):
            return ""
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n".join(parts).strip()

    @staticmethod
    def _friendly_tool_error_message(tool: str, text: str) -> str:
        lowered = (text or "").lower()
        if "leakless.exe" in lowered and "virus or potentially unwanted software" in lowered:
            return (
                f"工具 {tool} 执行失败：Windows 安全软件拦截了浏览器守护进程(leakless.exe)。\n"
                f"请在 Defender/杀毒软件中放行或添加排除后重试。"
            )
        return text

    def _normalize_mcp_tool_response(self, payload: Dict[str, Any], tool: str) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            return {"success": False, "error": f"Invalid MCP response for tool {tool}"}

        rpc_error = payload.get("error")
        if isinstance(rpc_error, dict):
            return {"success": False, "error": str(rpc_error.get("message") or rpc_error)}

        result = payload.get("result")
        if isinstance(result, dict):
            if result.get("isError"):
                text = self._extract_text_from_content(result.get("content"))
                error_text = text or f"Tool {tool} execution failed"
                return {"success": False, "error": self._friendly_tool_error_message(tool, error_text)}

            structured = result.get("structuredContent")
            if isinstance(structured, dict):
                if "success" not in structured:
                    structured["success"] = True
                return structured

            text = self._extract_text_from_content(result.get("content"))
            if text:
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        if "success" not in parsed:
                            parsed["success"] = True
                        return parsed
                except Exception:
                    pass
                return {"success": True, "message": text}

            if "success" not in result:
                result["success"] = True
            return result

        return {"success": True, "result": result}

    async def _call_tool_via_mcp(self, client: httpx.AsyncClient, tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._session_id:
            await self._mcp_initialize(client)

        def _headers():
            return {"Mcp-Session-Id": self._session_id} if self._session_id else {}

        payload = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": "tools/call",
            "params": {
                "name": tool,
                "arguments": params or {},
            },
        }

        resp = await client.post(
            f"{self.mcp_url}{self.mcp_endpoint}",
            headers=_headers(),
            json=payload,
        )

        # Session may expire; re-init once and retry.
        if resp.status_code in (400, 401, 403):
            if "session" in (resp.text or "").lower():
                self._session_id = None
                await self._mcp_initialize(client)
                resp = await client.post(
                    f"{self.mcp_url}{self.mcp_endpoint}",
                    headers=_headers(),
                    json=payload,
                )

        resp.raise_for_status()
        if not (resp.text or "").strip():
            return {
                "success": False,
                "error": f"MCP tool {tool} 返回空响应（HTTP {resp.status_code}）",
            }
        return self._normalize_mcp_tool_response(resp.json(), tool)

    async def _call_tool_via_legacy_http(self, client: httpx.AsyncClient, tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
        resp = await client.post(
            f"{self.mcp_url}/call",
            json={
                "tool": tool,
                "params": params or {},
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        if isinstance(payload, dict) and "success" not in payload:
            payload["success"] = True
        return payload

    async def call_tool(self, tool: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        if not self.ensure_running():
            return {"success": False, "error": "MCP service is not running and failed to start"}

        timeout_seconds = self._get_tool_timeout_seconds(tool)
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds)) as client:
                try:
                    return await self._call_tool_via_mcp(client, tool, params or {})
                except httpx.HTTPStatusError as mcp_error:
                    status = mcp_error.response.status_code if mcp_error.response is not None else None
                    # Backward compatibility for old xiaohongshu-mcp versions.
                    if status == 404:
                        logger.warning("MCP /mcp endpoint unavailable, fallback to legacy /call")
                        return await self._call_tool_via_legacy_http(client, tool, params or {})
                    raise
        except httpx.TimeoutException:
            return {"success": False, "error": f"MCP call timeout ({tool}, >{timeout_seconds}s)"}
        except Exception as exc:
            logger.error(f"MCP call failed: {exc}")
            return {"success": False, "error": str(exc)}

    def get_status(self) -> Dict[str, Any]:
        running = self.is_running()
        return {
            "running": running,
            "url": self.mcp_url,
            "binary_installed": self.binary_path.exists(),
            "binary_path": str(self.binary_path),
            "data_dir": str(self.data_dir),
            "pid": self.process.pid if self.process else None,
            "endpoint": self.mcp_endpoint,
        }


mcp_manager = MCPManager()
