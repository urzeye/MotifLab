import logging
import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def _get_project_root() -> Path:
    """获取项目根目录（处理包安装和直接运行两种情况）"""
    # 优先使用环境变量
    if os.getenv('RENDERINK_ROOT'):
        return Path(os.getenv('RENDERINK_ROOT'))

    # 尝试从当前工作目录查找配置文件
    cwd = Path.cwd()
    if (cwd / 'text_providers.yaml').exists():
        return cwd

    # 尝试从 __file__ 推断（直接运行时）
    config_py = Path(__file__)
    if config_py.exists():
        # backend/config.py -> 项目根目录
        potential_root = config_py.parent.parent
        if (potential_root / 'text_providers.yaml').exists():
            return potential_root

    # 默认返回当前工作目录
    return cwd


def _resolve_env_vars(value: Any) -> Any:
    """递归解析配置值中的环境变量占位符 ${VAR_NAME}"""
    if isinstance(value, str):
        pattern = re.compile(r'\$\{([^}]+)\}')

        def _replace(match: re.Match[str]) -> str:
            var_name = match.group(1)
            env_value = os.getenv(var_name)
            # 未设置时保留占位符，后续由校验阶段给出明确错误
            return env_value if env_value is not None else match.group(0)

        return pattern.sub(_replace, value)
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


def _contains_unresolved_env_var(value: Any) -> bool:
    """判断字符串中是否仍包含未解析的 ${VAR_NAME} 占位符"""
    return isinstance(value, str) and bool(re.search(r'\$\{[^}]+\}', value))


def _load_dotenv_file():
    """加载 .env（优先项目根目录，其次当前工作目录）"""
    env_path = _get_project_root() / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        logger.debug(f"已加载 .env 文件: {env_path}")
    else:
        load_dotenv()
        logger.debug(f"项目根目录未找到 .env: {env_path}，已尝试从工作目录加载")


_load_dotenv_file()


class Config:
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 12398
    CORS_ORIGINS = ['http://localhost:5173', 'http://localhost:3000']
    OUTPUT_DIR = 'output'
    # 允许多张较大参考图上传（例如 5 * 20MB）并留有协议开销余量
    MAX_CONTENT_LENGTH = 512 * 1024 * 1024

    _configs: Dict[str, Any] = {}

    @classmethod
    def _load_providers_config(cls, config_type: str, default_provider: str) -> Dict[str, Any]:
        """通用配置加载器"""
        cache_key = f'{config_type}_providers'
        if cache_key in cls._configs:
            return cls._configs[cache_key]

        config_path = _get_project_root() / f'{config_type}_providers.yaml'
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
        return cls._resolve_active_provider(config, 'google_genai')

    @classmethod
    def get_active_text_provider(cls) -> str:
        config = cls.load_text_providers_config()
        return cls._resolve_active_provider(config, 'google_gemini')

    @classmethod
    def _resolve_active_provider(cls, config: Dict[str, Any], default_provider: str) -> str:
        """解析当前激活服务商；无效时回退到第一个可用服务商。"""
        providers = config.get('providers', {}) or {}
        active_provider = (config.get('active_provider') or '').strip()

        if active_provider and active_provider in providers:
            return active_provider

        if providers:
            fallback = next(iter(providers.keys()))
            if active_provider:
                logger.warning(
                    f"active_provider='{active_provider}' 不存在，自动回退到可用服务商: {fallback}"
                )
            else:
                logger.warning(f"active_provider 为空，自动回退到可用服务商: {fallback}")
            return fallback

        return default_provider

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

        api_key = provider_config.get('api_key')
        if not api_key or _contains_unresolved_env_var(api_key):
            raise ValueError(f"服务商 {provider_name} 未配置 API Key")

        provider_type = provider_config.get('type', provider_name)
        base_url = provider_config.get('base_url')
        if provider_type in ['openai', 'openai_compatible', 'image_api'] and (
            not base_url or _contains_unresolved_env_var(base_url)
        ):
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
