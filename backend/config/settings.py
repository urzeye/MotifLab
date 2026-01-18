import logging
import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def _resolve_env_vars(value: Any) -> Any:
    """递归解析配置值中的环境变量占位符 ${VAR_NAME}"""
    if isinstance(value, str):
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, value)
        for var_name in matches:
            env_value = os.getenv(var_name, '')
            value = value.replace(f'${{{var_name}}}', env_value)
        return value
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


class Config:
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 12398
    CORS_ORIGINS = ['http://localhost:5173', 'http://localhost:3000']
    OUTPUT_DIR = 'output'

    _configs: Dict[str, Any] = {}

    @classmethod
    def _load_providers_config(cls, config_type: str, default_provider: str) -> Dict[str, Any]:
        """通用配置加载器"""
        cache_key = f'{config_type}_providers'
        if cache_key in cls._configs:
            return cls._configs[cache_key]

        config_path = Path(__file__).parent.parent / f'{config_type}_providers.yaml'
        logger.debug(f"加载{config_type}服务商配置: {config_path}")

        if not config_path.exists():
            logger.warning(f"{config_type}配置文件不存在: {config_path}，使用默认配置")
            cls._configs[cache_key] = {'active_provider': default_provider, 'providers': {}}
            return cls._configs[cache_key]

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f) or {}
            cls._configs[cache_key] = _resolve_env_vars(raw_config)
            logger.debug(f"{config_type}配置加载成功: {list(cls._configs[cache_key].get('providers', {}).keys())}")
        except yaml.YAMLError as e:
            logger.error(f"{config_type}配置文件 YAML 格式错误: {e}")
            raise ValueError(f"配置文件格式错误: {config_type}_providers.yaml\nYAML 解析错误: {e}")

        return cls._configs[cache_key]

    @classmethod
    def load_image_providers_config(cls) -> Dict[str, Any]:
        return cls._load_providers_config('image', 'google_genai')

    @classmethod
    def load_text_providers_config(cls) -> Dict[str, Any]:
        return cls._load_providers_config('text', 'google_gemini')

    @classmethod
    def get_active_image_provider(cls) -> str:
        config = cls.load_image_providers_config()
        return config.get('active_provider', 'google_genai')

    @classmethod
    def get_active_text_provider(cls) -> str:
        config = cls.load_text_providers_config()
        return config.get('active_provider', 'google_gemini')

    @classmethod
    def _get_provider_config(cls, config_type: str, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """通用获取服务商配置"""
        if config_type == 'image':
            config = cls.load_image_providers_config()
            provider_name = provider_name or cls.get_active_image_provider()
        else:
            config = cls.load_text_providers_config()
            provider_name = provider_name or cls.get_active_text_provider()

        providers = config.get('providers', {})
        if not providers:
            raise ValueError(f"未找到任何{config_type}生成服务商配置")

        if provider_name not in providers:
            available = ', '.join(providers.keys()) if providers else '无'
            raise ValueError(f"未找到{config_type}生成服务商配置: {provider_name}，可用: {available}")

        provider_config = providers[provider_name].copy()

        if not provider_config.get('api_key'):
            raise ValueError(f"服务商 {provider_name} 未配置 API Key")

        provider_type = provider_config.get('type', provider_name)
        if provider_type in ['openai', 'openai_compatible', 'image_api'] and not provider_config.get('base_url'):
            raise ValueError(f"服务商 {provider_name} 类型为 {provider_type}，需要配置 base_url")

        return provider_config

    @classmethod
    def get_image_provider_config(cls, provider_name: str = None) -> Dict[str, Any]:
        return cls._get_provider_config('image', provider_name)

    @classmethod
    def get_text_provider_config(cls, provider_name: str = None) -> Dict[str, Any]:
        return cls._get_provider_config('text', provider_name)

    @classmethod
    def reload_config(cls):
        """重新加载配置（清除缓存）"""
        logger.info("重新加载所有配置...")
        cls._configs.clear()


    @classmethod
    def list_text_providers(cls):
        config = cls.load_text_providers_config()
        return list(config.get('providers', {}).keys())

    @classmethod
    def list_image_providers(cls):
        config = cls.load_image_providers_config()
        return list(config.get('providers', {}).keys())


# Alias for cleaner API
Settings = Config


def get_settings():
    return Settings
