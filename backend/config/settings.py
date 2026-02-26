import logging
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import quote

import requests
import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

CONFIG_STORAGE_MODE_ENV = "CONFIG_STORAGE_MODE"
CONFIG_STORAGE_YAML = "yaml"
CONFIG_STORAGE_SUPABASE = "supabase"
DEFAULT_CONFIG_STORAGE_MODE = CONFIG_STORAGE_YAML

CONFIG_SUPABASE_TABLE_ENV = "CONFIG_SUPABASE_TABLE"
DEFAULT_CONFIG_SUPABASE_TABLE = "app_configs"

SEARCH_PROVIDER_FIRECRAWL = "firecrawl"
SEARCH_PROVIDER_EXA = "exa"
DEFAULT_FIRECRAWL_BASE_URL = "https://api.firecrawl.dev"
DEFAULT_EXA_BASE_URL = "https://api.exa.ai"


def _get_project_root() -> Path:
    """获取项目根目录（处理包安装和直接运行两种情况）"""
    # 优先使用环境变量
    custom_root = os.getenv("RENDERINK_ROOT")
    if custom_root:
        return Path(custom_root)

    cwd = Path.cwd()

    # 优先识别标准项目标记
    if (cwd / "pyproject.toml").exists() and (cwd / "backend").exists():
        return cwd

    # 兼容旧逻辑：通过配置文件判断根目录
    if (cwd / "text_providers.yaml").exists():
        return cwd

    # 尝试从当前文件推断
    # backend/config/settings.py -> 项目根目录
    config_py = Path(__file__).resolve()
    potential_root = config_py.parent.parent.parent
    if (potential_root / "pyproject.toml").exists():
        return potential_root

    return cwd


def _resolve_env_vars(value: Any) -> Any:
    """递归解析配置值中的环境变量占位符 ${VAR_NAME}"""
    if isinstance(value, str):
        pattern = re.compile(r"\$\{([^}]+)\}")

        def _replace(match: re.Match[str]) -> str:
            var_name = match.group(1)
            env_value = os.getenv(var_name)
            # 未设置时保留占位符，后续由校验阶段给出明确错误
            return env_value if env_value is not None else match.group(0)

        return pattern.sub(_replace, value)
    if isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


def _contains_unresolved_env_var(value: Any) -> bool:
    """判断字符串中是否仍包含未解析的 ${VAR_NAME} 占位符"""
    return isinstance(value, str) and bool(re.search(r"\$\{[^}]+\}", value))


def _load_dotenv_file():
    """加载 .env（优先项目根目录，其次当前工作目录）"""
    env_path = _get_project_root() / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.debug(f"已加载 .env 文件: {env_path}")
    else:
        load_dotenv()
        logger.debug(f"项目根目录未找到 .env: {env_path}，已尝试从工作目录加载")


class BaseConfigStore:
    """配置存储抽象基类。"""

    def load(self, config_name: str, default: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def save(self, config_name: str, config: Dict[str, Any]) -> None:
        raise NotImplementedError

    def describe(self) -> str:
        return self.__class__.__name__


class YamlConfigStore(BaseConfigStore):
    """YAML 文件配置存储（默认模式）。"""

    _FILE_MAPPING = {
        "text_providers": "text_providers.yaml",
        "image_providers": "image_providers.yaml",
        "search_providers": "search_providers.yaml",
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def _config_path(self, config_name: str) -> Path:
        filename = self._FILE_MAPPING.get(config_name, f"{config_name}.yaml")
        return self.project_root / filename

    def load(self, config_name: str, default: Dict[str, Any]) -> Dict[str, Any]:
        path = self._config_path(config_name)
        if not path.exists():
            logger.debug(f"配置文件不存在，使用默认配置: {path}")
            return deepcopy(default)

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            logger.error(f"配置文件 YAML 格式错误: {path}, error={e}")
            raise ValueError(f"配置文件格式错误: {path.name}\nYAML 解析错误: {e}")

        if not isinstance(data, dict):
            logger.warning(f"配置文件内容不是对象，回退默认值: {path}")
            return deepcopy(default)

        return data

    def save(self, config_name: str, config: Dict[str, Any]) -> None:
        path = self._config_path(config_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


class SupabaseConfigStore(BaseConfigStore):
    """Supabase 表配置存储（可选模式）。"""

    def __init__(self):
        self.table_name = os.getenv(CONFIG_SUPABASE_TABLE_ENV, DEFAULT_CONFIG_SUPABASE_TABLE).strip() \
            or DEFAULT_CONFIG_SUPABASE_TABLE

    def _get_credentials(self) -> tuple[str, str]:
        from backend.utils.supabase_client import SUPABASE_KEY, SUPABASE_URL
        return (SUPABASE_URL or "").rstrip("/"), (SUPABASE_KEY or "").strip()

    def _assert_credentials(self) -> tuple[str, str]:
        supabase_url, supabase_key = self._get_credentials()
        if not supabase_url or not supabase_key:
            raise ValueError(
                "Supabase 配置未就绪：请设置 SUPABASE_URL 和 SUPABASE_KEY，"
                "或将 CONFIG_STORAGE_MODE 切回 yaml"
            )
        return supabase_url, supabase_key

    def _request_headers(self, supabase_key: str, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
        }
        if extra:
            headers.update(extra)
        return headers

    def load(self, config_name: str, default: Dict[str, Any]) -> Dict[str, Any]:
        supabase_url, supabase_key = self._get_credentials()
        if not supabase_url or not supabase_key:
            logger.warning(
                "CONFIG_STORAGE_MODE=supabase 但未配置 SUPABASE_URL/SUPABASE_KEY，使用默认配置"
            )
            return deepcopy(default)

        key = quote(config_name, safe="")
        url = (
            f"{supabase_url}/rest/v1/{self.table_name}"
            f"?select=config_data&config_key=eq.{key}&limit=1"
        )

        try:
            response = requests.get(url, headers=self._request_headers(supabase_key), timeout=15)
            if response.status_code == 404:
                logger.warning(
                    f"Supabase 配置表不存在: {self.table_name}，回退默认配置（config={config_name}）"
                )
                return deepcopy(default)
            response.raise_for_status()
            rows = response.json()
        except Exception as e:
            logger.error(f"从 Supabase 读取配置失败: config={config_name}, error={e}")
            return deepcopy(default)

        if not isinstance(rows, list) or not rows:
            return deepcopy(default)

        config_data = rows[0].get("config_data")
        if not isinstance(config_data, dict):
            logger.warning(f"Supabase 配置数据格式异常，回退默认: config={config_name}")
            return deepcopy(default)
        return config_data

    def save(self, config_name: str, config: Dict[str, Any]) -> None:
        supabase_url, supabase_key = self._assert_credentials()
        url = f"{supabase_url}/rest/v1/{self.table_name}?on_conflict=config_key"
        payload = [{"config_key": config_name, "config_data": config}]
        headers = self._request_headers(
            supabase_key,
            extra={"Prefer": "resolution=merge-duplicates,return=representation"},
        )

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            if response.status_code == 404:
                raise ValueError(
                    f"Supabase 配置表不存在: {self.table_name}。"
                    "请先执行迁移 SQL 创建 app_configs 表。"
                )
            response.raise_for_status()
        except Exception as e:
            raise ValueError(f"保存配置到 Supabase 失败: {e}") from e


_load_dotenv_file()


class Config:
    DEBUG = True
    HOST = "0.0.0.0"
    PORT = 12398
    CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]
    OUTPUT_DIR = "output"
    # 允许多张较大参考图上传（例如 5 * 20MB）并留有协议开销余量
    MAX_CONTENT_LENGTH = 512 * 1024 * 1024

    _configs: Dict[str, Any] = {}
    _store: Optional[BaseConfigStore] = None
    _store_mode: Optional[str] = None

    @classmethod
    def _normalize_storage_mode(cls, raw_mode: Optional[str]) -> str:
        mode = (raw_mode or DEFAULT_CONFIG_STORAGE_MODE).strip().lower()
        if mode in {"", "yaml", "file", "files"}:
            return CONFIG_STORAGE_YAML
        if mode in {"supabase", "postgres", "postgresql"}:
            return CONFIG_STORAGE_SUPABASE

        logger.warning(f"未知配置存储模式 '{raw_mode}'，已回退为 yaml")
        return CONFIG_STORAGE_YAML

    @classmethod
    def get_config_storage_mode(cls) -> str:
        return cls._normalize_storage_mode(os.getenv(CONFIG_STORAGE_MODE_ENV))

    @classmethod
    def _get_store(cls) -> BaseConfigStore:
        mode = cls.get_config_storage_mode()
        if cls._store and cls._store_mode == mode:
            return cls._store

        if mode == CONFIG_STORAGE_SUPABASE:
            cls._store = SupabaseConfigStore()
        else:
            cls._store = YamlConfigStore(_get_project_root())

        cls._store_mode = mode
        logger.info(f"配置存储模式: {mode} ({cls._store.describe()})")
        return cls._store

    @classmethod
    def _load_config_document(
        cls,
        cache_key: str,
        config_name: str,
        default: Dict[str, Any],
    ) -> Dict[str, Any]:
        if cache_key in cls._configs:
            return cls._configs[cache_key]

        store = cls._get_store()
        raw_config = store.load(config_name, deepcopy(default))
        resolved = _resolve_env_vars(raw_config)
        if not isinstance(resolved, dict):
            logger.warning(f"配置文档格式异常，回退默认: {config_name}")
            resolved = deepcopy(default)

        cls._configs[cache_key] = resolved
        return cls._configs[cache_key]

    @classmethod
    def _save_config_document(cls, cache_key: str, config_name: str, config: Dict[str, Any]) -> None:
        if not isinstance(config, dict):
            raise ValueError("配置对象必须是 JSON 对象")

        store = cls._get_store()
        store.save(config_name, deepcopy(config))

        # 清理缓存，保证后续读取到最新配置
        cls._configs.pop(cache_key, None)

    @classmethod
    def _default_provider_config(cls, default_provider: str) -> Dict[str, Any]:
        return {"active_provider": default_provider, "providers": {}}

    @classmethod
    def load_image_providers_config(cls) -> Dict[str, Any]:
        config = cls._load_config_document(
            cache_key="image_providers",
            config_name="image_providers",
            default=cls._default_provider_config("google_genai"),
        )
        if not isinstance(config.get("providers"), dict):
            config["providers"] = {}
        config["active_provider"] = str(config.get("active_provider") or "").strip()
        return config

    @classmethod
    def save_image_providers_config(cls, config: Dict[str, Any]) -> None:
        cls._save_config_document("image_providers", "image_providers", config)

    @classmethod
    def load_text_providers_config(cls) -> Dict[str, Any]:
        config = cls._load_config_document(
            cache_key="text_providers",
            config_name="text_providers",
            default=cls._default_provider_config("google_gemini"),
        )
        if not isinstance(config.get("providers"), dict):
            config["providers"] = {}
        config["active_provider"] = str(config.get("active_provider") or "").strip()
        return config

    @classmethod
    def save_text_providers_config(cls, config: Dict[str, Any]) -> None:
        cls._save_config_document("text_providers", "text_providers", config)

    @classmethod
    def _default_search_providers_config(cls) -> Dict[str, Any]:
        return {
            "active_provider": SEARCH_PROVIDER_FIRECRAWL,
            "providers": {
                SEARCH_PROVIDER_FIRECRAWL: {
                    "type": SEARCH_PROVIDER_FIRECRAWL,
                    "enabled": False,
                    "api_key": "",
                    "base_url": "",
                },
                SEARCH_PROVIDER_EXA: {
                    "type": SEARCH_PROVIDER_EXA,
                    "enabled": False,
                    "api_key": "",
                    "base_url": "",
                },
            },
        }

    @classmethod
    def _normalize_search_provider_item(cls, provider_name: str, item: Any) -> Dict[str, Any]:
        normalized = item.copy() if isinstance(item, dict) else {}
        provider_type = str(normalized.get("type") or provider_name).strip().lower() or provider_name
        normalized["type"] = provider_type
        normalized["enabled"] = bool(normalized.get("enabled", False))
        normalized["api_key"] = (normalized.get("api_key") or "").strip()
        normalized["base_url"] = (normalized.get("base_url") or "").strip()
        return normalized

    @classmethod
    def _normalize_search_providers_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        raw_providers = config.get("providers")
        providers: Dict[str, Any] = {}

        if isinstance(raw_providers, dict) and raw_providers:
            for name, provider_item in raw_providers.items():
                provider_name = str(name or "").strip()
                if not provider_name:
                    continue
                providers[provider_name] = cls._normalize_search_provider_item(provider_name, provider_item)
        else:
            providers = deepcopy(cls._default_search_providers_config()["providers"])

        # 保证 firecrawl/exa 至少存在
        if SEARCH_PROVIDER_FIRECRAWL not in providers:
            providers[SEARCH_PROVIDER_FIRECRAWL] = cls._normalize_search_provider_item(
                SEARCH_PROVIDER_FIRECRAWL,
                cls._default_search_providers_config()["providers"][SEARCH_PROVIDER_FIRECRAWL],
            )
        if SEARCH_PROVIDER_EXA not in providers:
            providers[SEARCH_PROVIDER_EXA] = cls._normalize_search_provider_item(
                SEARCH_PROVIDER_EXA,
                cls._default_search_providers_config()["providers"][SEARCH_PROVIDER_EXA],
            )

        active_provider = str(config.get("active_provider") or "").strip()
        if not active_provider or active_provider not in providers:
            active_provider = cls._resolve_active_provider(
                {"active_provider": active_provider, "providers": providers},
                SEARCH_PROVIDER_FIRECRAWL,
            )

        return {
            "active_provider": active_provider,
            "providers": providers,
        }

    @classmethod
    def load_search_providers_config(cls) -> Dict[str, Any]:
        config = cls._load_config_document(
            cache_key="search_providers",
            config_name="search_providers",
            default=cls._default_search_providers_config(),
        )
        normalized = cls._normalize_search_providers_config(config if isinstance(config, dict) else {})
        cls._configs["search_providers"] = normalized
        return normalized

    @classmethod
    def save_search_providers_config(cls, config: Dict[str, Any]) -> None:
        normalized = cls._normalize_search_providers_config(config if isinstance(config, dict) else {})
        cls._save_config_document("search_providers", "search_providers", normalized)

    @classmethod
    def get_active_search_provider(cls) -> str:
        config = cls.load_search_providers_config()
        return cls._resolve_active_provider(config, SEARCH_PROVIDER_FIRECRAWL)

    @classmethod
    def get_search_provider_config(
        cls,
        provider_name: Optional[str] = None,
        require_enabled: bool = True,
    ) -> Dict[str, Any]:
        search_config = cls.load_search_providers_config()
        providers = search_config.get("providers") or {}
        if not providers:
            raise ValueError("未找到任何搜索服务商配置")

        provider_name = provider_name or cls.get_active_search_provider()
        if provider_name not in providers:
            available = ", ".join(providers.keys())
            raise ValueError(f"未找到搜索服务商配置: {provider_name}，可用: {available}")

        provider_config = providers[provider_name].copy()
        provider_type = (provider_config.get("type") or provider_name).strip().lower()
        provider_config["type"] = provider_type

        if require_enabled and not bool(provider_config.get("enabled", False)):
            raise ValueError(f"搜索服务商 [{provider_name}] 未启用")

        if provider_type == SEARCH_PROVIDER_EXA and not (provider_config.get("api_key") or "").strip():
            raise ValueError(f"搜索服务商 [{provider_name}] 未配置 API Key")

        if not (provider_config.get("base_url") or "").strip():
            if provider_type == SEARCH_PROVIDER_FIRECRAWL:
                provider_config["base_url"] = DEFAULT_FIRECRAWL_BASE_URL
            elif provider_type == SEARCH_PROVIDER_EXA:
                provider_config["base_url"] = DEFAULT_EXA_BASE_URL

        return provider_config

    @classmethod
    def get_active_image_provider(cls) -> str:
        config = cls.load_image_providers_config()
        return cls._resolve_active_provider(config, "google_genai")

    @classmethod
    def get_active_text_provider(cls) -> str:
        config = cls.load_text_providers_config()
        return cls._resolve_active_provider(config, "google_gemini")

    @classmethod
    def _resolve_active_provider(cls, config: Dict[str, Any], default_provider: str) -> str:
        """解析当前激活服务商；无效时回退到第一个可用服务商。"""
        providers = config.get("providers", {}) or {}
        active_provider = (config.get("active_provider") or "").strip()

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
        if config_type == "image":
            config = cls.load_image_providers_config()
            provider_name = provider_name or cls.get_active_image_provider()
        else:
            config = cls.load_text_providers_config()
            provider_name = provider_name or cls.get_active_text_provider()

        providers = config.get("providers", {})
        if not providers:
            raise ValueError(f"未找到任何{config_type}生成服务商配置")

        if provider_name not in providers:
            available = ", ".join(providers.keys()) if providers else "无"
            raise ValueError(f"未找到{config_type}生成服务商配置: {provider_name}，可用: {available}")

        provider_config = providers[provider_name].copy()

        api_key = provider_config.get("api_key")
        if not api_key or _contains_unresolved_env_var(api_key):
            raise ValueError(f"服务商 {provider_name} 未配置 API Key")

        provider_type = provider_config.get("type", provider_name)
        base_url = provider_config.get("base_url")
        if provider_type in ["openai", "openai_compatible", "image_api"] and (
            not base_url or _contains_unresolved_env_var(base_url)
        ):
            raise ValueError(f"服务商 {provider_name} 类型为 {provider_type}，需要配置 base_url")

        return provider_config

    @classmethod
    def get_image_provider_config(cls, provider_name: str = None) -> Dict[str, Any]:
        return cls._get_provider_config("image", provider_name)

    @classmethod
    def get_text_provider_config(cls, provider_name: str = None) -> Dict[str, Any]:
        return cls._get_provider_config("text", provider_name)

    @classmethod
    def reload_config(cls):
        """重新加载配置（清除缓存）"""
        logger.info("重新加载所有配置...")
        cls._configs.clear()
        cls._store = None
        cls._store_mode = None


Settings = Config


def get_settings():
    return Settings
