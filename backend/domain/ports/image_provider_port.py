"""图片生成服务商端口协议。"""

from __future__ import annotations

from typing import Any, Dict, Protocol


class ImageProviderPort(Protocol):
    """图片生成适配器端口。"""

    def generate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """执行图片生成。"""
        ...

    def validate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """校验服务商配置或连通性。"""
        ...

    def get_capability(self) -> Dict[str, Any]:
        """返回模型能力描述。"""
        ...
