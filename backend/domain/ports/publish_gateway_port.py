"""发布网关端口协议。"""

from __future__ import annotations

from typing import Any, Dict, Protocol


class PublishGatewayPort(Protocol):
    """发布能力适配器端口。"""

    def check_login(self) -> Dict[str, Any]:
        """检查发布平台登录状态。"""
        ...

    def publish(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """发布图文内容。"""
        ...

    def publish_video(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """发布视频内容。"""
        ...
