"""服务商配置解析服务。"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from backend.config import ConfigService, get_config_service


class ProviderConfigService:
    """统一解析文本/图片服务商配置，减少重复配置读取逻辑。"""

    def __init__(self, config_service: ConfigService | None = None):
        self.config_service = config_service or get_config_service()

    def get_active_text_provider(self) -> str:
        """获取当前激活的文本服务商名称。"""
        return self.config_service.get_active_text_provider()

    def get_active_image_provider(self) -> str:
        """获取当前激活的图片服务商名称。"""
        return self.config_service.get_active_image_provider()

    def resolve_text_provider_config(
        self,
        provider_config: Optional[Dict[str, Any]] = None,
        provider_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """解析可用的文本服务商配置。"""
        if isinstance(provider_config, dict) and provider_config:
            return provider_config

        resolved_provider_name = provider_name or self.get_active_text_provider()
        return self.config_service.get_text_provider_config(resolved_provider_name)

    def resolve_image_provider_config(
        self,
        provider_config: Optional[Dict[str, Any]] = None,
        provider_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """解析可用的图片服务商配置。"""
        if isinstance(provider_config, dict) and provider_config:
            return provider_config

        resolved_provider_name = provider_name or self.get_active_image_provider()
        return self.config_service.get_image_provider_config(resolved_provider_name)

    def build_provider_bundle(
        self,
        logger: logging.Logger | None = None,
        swallow_errors: bool = True,
    ) -> Dict[str, Any]:
        """构建包含文本与图片配置的 provider bundle。"""
        bundle: Dict[str, Any] = {}

        try:
            text_provider = self.get_active_text_provider()
            bundle["text_provider"] = self.resolve_text_provider_config(provider_name=text_provider)
        except Exception as exc:
            if logger:
                logger.warning(f"获取文本服务商配置失败: {exc}")
            if not swallow_errors:
                raise
            bundle["text_provider"] = {}

        try:
            image_provider = self.get_active_image_provider()
            bundle["image_provider"] = self.resolve_image_provider_config(provider_name=image_provider)
        except Exception as exc:
            if logger:
                logger.warning(f"获取图片服务商配置失败: {exc}")
            if not swallow_errors:
                raise
            bundle["image_provider"] = {}

        return bundle


_provider_config_service_instance: Optional[ProviderConfigService] = None


def get_provider_config_service() -> ProviderConfigService:
    """获取全局服务商配置解析服务实例。"""
    global _provider_config_service_instance
    if _provider_config_service_instance is None:
        _provider_config_service_instance = ProviderConfigService()
    return _provider_config_service_instance
