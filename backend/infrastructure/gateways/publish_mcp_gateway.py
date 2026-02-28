"""MCP 发布网关实现。"""

from __future__ import annotations

from typing import Any, Dict

from backend.domain.ports import PublishGatewayPort
from backend.utils.mcp_manager import mcp_manager


class McpPublishGateway(PublishGatewayPort):
    """基于 xiaohongshu-mcp 的发布网关。"""

    async def check_login(self) -> Dict[str, Any]:
        return await mcp_manager.call_tool("check_login_status")

    async def publish(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await mcp_manager.call_tool("publish_content", payload)

    async def publish_video(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await mcp_manager.call_tool("publish_with_video", payload)

    async def open_login_page(self) -> Dict[str, Any]:
        # Older MCP versions expose `open_login_page`, while newer versions
        # provide `get_login_qrcode`.
        result = await mcp_manager.call_tool("open_login_page")
        if result.get("success", True):
            return result

        error_text = str(result.get("error") or "")
        if "unknown tool" in error_text and "open_login_page" in error_text:
            qr_result = await mcp_manager.call_tool("get_login_qrcode")
            if qr_result.get("success", False):
                if "message" not in qr_result:
                    qr_result["message"] = "请使用小红书扫码登录"
                qr_result["login_mode"] = "qrcode"
            return qr_result

        return result

    def get_status(self) -> Dict[str, Any]:
        return mcp_manager.get_status()

    def install_binary(self) -> Dict[str, Any]:
        return mcp_manager.install_binary()

    async def list_posts(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await mcp_manager.call_tool("list_feeds", payload)

    async def search_posts(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await mcp_manager.call_tool("search_feeds", payload)


_publish_gateway: McpPublishGateway | None = None


def get_publish_gateway() -> McpPublishGateway:
    """获取发布网关单例。"""
    global _publish_gateway
    if _publish_gateway is None:
        _publish_gateway = McpPublishGateway()
    return _publish_gateway
