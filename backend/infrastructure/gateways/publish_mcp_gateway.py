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
        return await mcp_manager.call_tool("open_login_page")

    def get_status(self) -> Dict[str, Any]:
        return mcp_manager.get_status()

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
