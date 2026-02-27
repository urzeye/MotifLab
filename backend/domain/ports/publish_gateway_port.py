"""发布网关端口协议。"""

from __future__ import annotations

from typing import Any, Dict, Protocol


class PublishGatewayPort(Protocol):
    """发布能力适配器端口。"""

    async def check_login(self) -> Dict[str, Any]:
        """检查发布平台登录状态。"""
        ...

    async def publish(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """发布图文内容。"""
        ...

    async def publish_video(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """发布视频内容。"""
        ...

    async def open_login_page(self) -> Dict[str, Any]:
        """打开登录页。"""
        ...

    def get_status(self) -> Dict[str, Any]:
        """获取网关运行状态。"""
        ...

    async def list_posts(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """获取帖子列表。"""
        ...

    async def search_posts(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """搜索帖子。"""
        ...
