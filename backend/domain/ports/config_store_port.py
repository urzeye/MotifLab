"""配置存储端口协议。"""

from __future__ import annotations

from typing import Any, Dict, Protocol


class ConfigStorePort(Protocol):
    """配置存储抽象端口。"""

    def load(self, config_name: str, default: Dict[str, Any]) -> Dict[str, Any]:
        """加载配置文档。"""
        ...

    def save(self, config_name: str, config: Dict[str, Any]) -> None:
        """保存配置文档。"""
        ...

    def describe(self) -> str:
        """返回存储实现描述。"""
        ...
