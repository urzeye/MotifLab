"""统一配置服务入口。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .settings import Config


class ConfigService:
    """配置服务，统一封装配置读写与服务商解析能力。"""

    def get_config_storage_mode(self) -> str:
        return Config.get_config_storage_mode()

    def load_image_providers_config(self) -> Dict[str, Any]:
        return Config.load_image_providers_config()

    def save_image_providers_config(self, config: Dict[str, Any]) -> None:
        Config.save_image_providers_config(config)

    def load_text_providers_config(self) -> Dict[str, Any]:
        return Config.load_text_providers_config()

    def save_text_providers_config(self, config: Dict[str, Any]) -> None:
        Config.save_text_providers_config(config)

    def load_search_providers_config(self) -> Dict[str, Any]:
        return Config.load_search_providers_config()

    def save_search_providers_config(self, config: Dict[str, Any]) -> None:
        Config.save_search_providers_config(config)

    def get_active_search_provider(self) -> str:
        return Config.get_active_search_provider()

    def get_search_provider_config(
        self,
        provider_name: Optional[str] = None,
        require_enabled: bool = True,
    ) -> Dict[str, Any]:
        return Config.get_search_provider_config(provider_name, require_enabled=require_enabled)

    def get_active_image_provider(self) -> str:
        return Config.get_active_image_provider()

    def get_image_provider_config(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        return Config.get_image_provider_config(provider_name)

    def get_active_text_provider(self) -> str:
        return Config.get_active_text_provider()

    def get_text_provider_config(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        return Config.get_text_provider_config(provider_name)

    def reload(self) -> None:
        Config.reload_config()


_config_service_instance: Optional[ConfigService] = None


def get_config_service() -> ConfigService:
    """获取全局配置服务实例。"""
    global _config_service_instance
    if _config_service_instance is None:
        _config_service_instance = ConfigService()
    return _config_service_instance
