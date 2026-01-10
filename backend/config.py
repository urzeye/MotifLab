import logging
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


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
                cls._configs[cache_key] = yaml.safe_load(f) or {}
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
