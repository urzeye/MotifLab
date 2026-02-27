"""应用依赖容器。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from backend.config import ConfigService, get_config_service
from backend.infrastructure.services.search_service import build_default_search_provider_registry


@dataclass
class AppContainer:
    """统一维护应用级依赖，便于后续适配器扩展。"""

    config_service: ConfigService
    adapters: Dict[str, Any] = field(default_factory=dict)

    def register_adapter(self, name: str, adapter: Any) -> None:
        """注册适配器实例（如搜索适配器、数据库适配器）。"""
        self.adapters[name] = adapter

    def get_adapter(self, name: str) -> Any:
        """获取已注册适配器。"""
        return self.adapters.get(name)


def build_container() -> AppContainer:
    """构建默认容器。"""
    container = AppContainer(config_service=get_config_service())
    container.register_adapter("search_provider_registry", build_default_search_provider_registry())
    return container
