"""
xiaohongshu-mcp 进程管理器

管理 xiaohongshu-mcp 服务的启动、停止和状态检查。
"""

import os
import subprocess
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)


class MCPManager:
    """
    管理 xiaohongshu-mcp 进程

    功能：
    - 自动检测 MCP 服务是否运行
    - 自动启动 MCP 服务
    - 提供 MCP API 调用接口
    """

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.binary_path = self.project_root / "tools" / "xiaohongshu-mcp" / "xiaohongshu-mcp"
        self.data_dir = self.project_root / "data" / "xiaohongshu"
        self.logs_dir = self.project_root / "logs"
        self.mcp_url = "http://localhost:18060"
        self.process: Optional[subprocess.Popen] = None

    def is_running(self) -> bool:
        """检查 MCP 服务是否运行"""
        try:
            resp = httpx.get(f"{self.mcp_url}/health", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False

    def start(self, timeout: int = 30) -> bool:
        """
        启动 MCP 服务

        Args:
            timeout: 启动超时时间（秒）

        Returns:
            bool: 是否启动成功
        """
        if self.is_running():
            logger.info("MCP 服务已在运行")
            return True

        if not self.binary_path.exists():
            logger.error(f"xiaohongshu-mcp 未安装，请运行 scripts/install-tools.sh")
            raise FileNotFoundError(
                f"xiaohongshu-mcp 未安装。\n"
                f"请运行: ./scripts/install-tools.sh\n"
                f"或手动下载到: {self.binary_path}"
            )

        # 确保数据目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # 日志文件
        log_file = self.logs_dir / "mcp.log"

        logger.info(f"启动 xiaohongshu-mcp 服务...")

        try:
            # 打开日志文件
            with open(log_file, "a") as f:
                self.process = subprocess.Popen(
                    [
                        str(self.binary_path),
                        f"--port=18060",
                        f"--data-dir={self.data_dir}",
                    ],
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    cwd=str(self.project_root),
                )

            # 等待服务启动
            for i in range(timeout):
                time.sleep(1)
                if self.is_running():
                    logger.info(f"MCP 服务已启动 (PID: {self.process.pid})")
                    return True

            logger.error(f"MCP 服务启动超时 ({timeout}秒)")
            return False

        except Exception as e:
            logger.error(f"启动 MCP 服务失败: {e}")
            return False

    def stop(self):
        """停止 MCP 服务"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                logger.info("MCP 服务已停止")
            except Exception as e:
                logger.warning(f"停止 MCP 服务失败: {e}")
                self.process.kill()
            finally:
                self.process = None

    def ensure_running(self) -> bool:
        """确保 MCP 服务运行，如果未运行则启动"""
        if not self.is_running():
            return self.start()
        return True

    async def call_tool(self, tool: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        调用 MCP 工具

        Args:
            tool: 工具名称，如 'check_login_status', 'publish_content'
            params: 工具参数

        Returns:
            dict: 工具返回结果
        """
        if not self.ensure_running():
            return {
                "success": False,
                "error": "MCP 服务未运行且无法启动"
            }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self.mcp_url}/call",
                    json={
                        "tool": tool,
                        "params": params or {}
                    }
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "MCP 调用超时"
            }
        except Exception as e:
            logger.error(f"MCP 调用失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_status(self) -> Dict[str, Any]:
        """获取 MCP 服务状态"""
        running = self.is_running()
        return {
            "running": running,
            "url": self.mcp_url,
            "binary_installed": self.binary_path.exists(),
            "binary_path": str(self.binary_path),
            "data_dir": str(self.data_dir),
            "pid": self.process.pid if self.process else None
        }


# 全局单例实例
mcp_manager = MCPManager()
