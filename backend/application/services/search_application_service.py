"""搜索应用层服务。"""

from __future__ import annotations

from typing import Any

from backend.config import ConfigService, get_config_service
from backend.infrastructure.services.search_service import (
    get_search_provider,
    is_valid_http_url,
    test_provider,
)

_search_application_service: SearchApplicationService | None = None


class SearchApplicationService:
    """封装搜索抓取相关的应用层编排。"""

    def __init__(self, config_service: ConfigService | None = None) -> None:
        self._config_service = config_service or get_config_service()

    def is_valid_http_url(self, url: str) -> bool:
        """校验 URL 是否为 http/https。"""
        return is_valid_http_url(url)

    def get_search_provider_config(
        self,
        provider_name: str | None = None,
        require_enabled: bool = True,
    ) -> dict[str, Any]:
        """读取并校验搜索服务商配置。"""
        return self._config_service.get_search_provider_config(provider_name, require_enabled=require_enabled)

    def build_provider_status(self, provider_name: str | None = None) -> dict[str, Any]:
        """构建搜索服务状态响应数据。"""
        resolved_provider_name = provider_name or self._config_service.get_active_search_provider()
        search_config = self._config_service.load_search_providers_config()
        providers = search_config.get("providers") or {}
        provider_config = providers.get(resolved_provider_name) or {}

        has_api_key = bool((provider_config.get("api_key") or "").strip())
        has_base_url = bool((provider_config.get("base_url") or "").strip())
        return {
            "active_provider": search_config.get("active_provider"),
            "provider": resolved_provider_name,
            "enabled": bool(provider_config.get("enabled", False)),
            "configured": has_api_key or has_base_url,
        }

    @staticmethod
    def create_provider(provider_type: str, registry: Any = None):
        """根据服务商类型创建抓取适配器。"""
        if registry is not None:
            return registry.create(provider_type)
        return get_search_provider(provider_type)

    def scrape_url(self, url: str, provider_name: str | None = None, registry: Any = None) -> dict[str, Any]:
        """抓取网页并返回结构化内容。"""
        provider_config = self.get_search_provider_config(provider_name, require_enabled=True)
        provider_type = (provider_config.get("type") or "").strip().lower()
        provider = self.create_provider(provider_type, registry=registry)
        return provider.scrape(url, provider_config)

    @staticmethod
    def test_provider_connection(provider_type: str, config: dict[str, Any]) -> dict[str, Any]:
        """测试搜索服务商连接。"""
        return test_provider(provider_type, config)


def get_search_application_service() -> SearchApplicationService:
    """获取搜索应用层服务单例。"""
    global _search_application_service
    if _search_application_service is None:
        _search_application_service = SearchApplicationService()
    return _search_application_service
