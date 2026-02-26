"""搜索抓取服务抽象（支持 Firecrawl / Exa）。"""

from __future__ import annotations

import logging
from typing import Any, Dict
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

DEFAULT_FIRECRAWL_BASE_URL = "https://api.firecrawl.dev"
DEFAULT_EXA_BASE_URL = "https://api.exa.ai"


def is_valid_http_url(url: str) -> bool:
    """校验 URL 是否是 http/https。"""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def _normalize_text(value: Any) -> str:
    """将多种类型安全转换为文本。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "\n".join(str(item) for item in value if str(item).strip()).strip()
    return str(value).strip()


def _extract_error_message(response: requests.Response, fallback: str) -> str:
    """从响应中提取更具体的错误信息。"""
    try:
        payload = response.json()
        if isinstance(payload, dict):
            for key in ("error", "message", "detail"):
                value = payload.get(key)
                if value:
                    return _normalize_text(value)
    except Exception:
        pass
    return fallback


class BaseSearchProvider:
    """搜索抓取服务商基类。"""

    provider_type = "base"

    def scrape(self, url: str, config: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """默认测试逻辑：抓取 example.com。"""
        result = self.scrape("https://example.com", config)
        if result.get("success"):
            return {
                "success": True,
                "message": f"{self.provider_type} 连接成功，可以抓取网页内容",
            }
        return {
            "success": False,
            "message": result.get("error") or f"{self.provider_type} 连接失败",
        }


class FirecrawlSearchProvider(BaseSearchProvider):
    """Firecrawl 抓取实现。"""

    provider_type = "firecrawl"

    def scrape(self, url: str, config: Dict[str, Any]) -> Dict[str, Any]:
        base_url = (config.get("base_url") or DEFAULT_FIRECRAWL_BASE_URL).rstrip("/")
        api_key = (config.get("api_key") or "").strip()

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {"url": url, "formats": ["markdown"]}
        endpoints = [f"{base_url}/v2/scrape", f"{base_url}/v1/scrape"]
        errors: list[str] = []

        logger.info(f"🌐 Firecrawl 开始抓取: {url}")

        for index, api_url in enumerate(endpoints):
            try:
                response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            except requests.exceptions.Timeout:
                return {"success": False, "error": "抓取超时，请稍后重试"}
            except requests.exceptions.ConnectionError:
                return {"success": False, "error": f"无法连接到 Firecrawl 服务: {base_url}"}

            if response.status_code == 404 and index == 0:
                # v2 在某些自建/旧版本实例中不存在，自动回退 v1
                continue

            if response.status_code != 200:
                if response.status_code == 401:
                    return {"success": False, "error": "Firecrawl API Key 无效或未提供"}
                if response.status_code == 402:
                    return {"success": False, "error": "Firecrawl API 配额已用尽"}
                if response.status_code == 429:
                    return {"success": False, "error": "Firecrawl 请求过于频繁，请稍后重试"}
                errors.append(
                    _extract_error_message(
                        response,
                        f"Firecrawl 请求失败: HTTP {response.status_code}",
                    )
                )
                continue

            try:
                payload_json = response.json()
            except Exception:
                return {"success": False, "error": "Firecrawl 返回了无法解析的响应"}

            data = payload_json.get("data") if isinstance(payload_json, dict) else {}
            if isinstance(data, list):
                data = data[0] if data else {}
            if not isinstance(data, dict):
                data = {}

            metadata = data.get("metadata") or {}
            title = (
                _normalize_text(metadata.get("title"))
                or _normalize_text(metadata.get("ogTitle"))
                or _normalize_text(data.get("title"))
                or "未命名网页"
            )
            content = (
                _normalize_text(data.get("markdown"))
                or _normalize_text(data.get("content"))
                or _normalize_text(data.get("text"))
            )

            if not content:
                return {"success": False, "error": "网页抓取成功但未提取到正文内容"}

            logger.info(f"✅ Firecrawl 抓取完成: title={title[:60]}..., chars={len(content)}")
            return {
                "success": True,
                "data": {
                    "title": title,
                    "content": content,
                    "word_count": len(content),
                    "url": url,
                },
            }

        if errors:
            return {"success": False, "error": errors[-1]}
        return {"success": False, "error": "Firecrawl 抓取失败，请检查配置"}


class ExaSearchProvider(BaseSearchProvider):
    """Exa 抓取实现（通过 /contents 提取指定 URL 正文）。"""

    provider_type = "exa"

    def scrape(self, url: str, config: Dict[str, Any]) -> Dict[str, Any]:
        base_url = (config.get("base_url") or DEFAULT_EXA_BASE_URL).rstrip("/")
        api_key = (config.get("api_key") or "").strip()

        if not api_key:
            return {"success": False, "error": "Exa API Key 未配置"}

        api_url = f"{base_url}/contents"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "Authorization": f"Bearer {api_key}",
        }
        payload = {
            "urls": [url],
            "text": True,
        }

        logger.info(f"🌐 Exa 开始抓取: {url}")

        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        except requests.exceptions.Timeout:
            return {"success": False, "error": "抓取超时，请稍后重试"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": f"无法连接到 Exa 服务: {base_url}"}

        if response.status_code != 200:
            if response.status_code == 401:
                return {"success": False, "error": "Exa API Key 无效或未提供"}
            if response.status_code == 402:
                return {"success": False, "error": "Exa API 配额已用尽"}
            if response.status_code == 429:
                return {"success": False, "error": "Exa 请求过于频繁，请稍后重试"}
            return {
                "success": False,
                "error": _extract_error_message(
                    response,
                    f"Exa 请求失败: HTTP {response.status_code}",
                ),
            }

        try:
            payload_json = response.json()
        except Exception:
            return {"success": False, "error": "Exa 返回了无法解析的响应"}

        results = payload_json.get("results") if isinstance(payload_json, dict) else None
        if not isinstance(results, list) or not results:
            return {"success": False, "error": "Exa 抓取成功但未返回有效结果"}

        first = results[0] if isinstance(results[0], dict) else {}
        title = _normalize_text(first.get("title")) or "未命名网页"
        content = (
            _normalize_text(first.get("text"))
            or _normalize_text(first.get("content"))
            or _normalize_text(first.get("summary"))
        )

        if not content:
            return {"success": False, "error": "Exa 抓取成功但未提取到正文内容"}

        logger.info(f"✅ Exa 抓取完成: title={title[:60]}..., chars={len(content)}")
        return {
            "success": True,
            "data": {
                "title": title,
                "content": content,
                "word_count": len(content),
                "url": url,
            },
        }


def get_search_provider(provider_type: str) -> BaseSearchProvider:
    """按 provider type 获取抓取实现。"""
    normalized = (provider_type or "").strip().lower()
    if normalized == "firecrawl":
        return FirecrawlSearchProvider()
    if normalized == "exa":
        return ExaSearchProvider()
    raise ValueError(f"不支持的搜索服务商: {provider_type}")


def scrape_with_provider(url: str, provider_config: Dict[str, Any]) -> Dict[str, Any]:
    """使用指定 provider 配置抓取网页。"""
    provider_type = (provider_config.get("type") or "").strip().lower()
    provider = get_search_provider(provider_type)
    return provider.scrape(url, provider_config)


def test_provider(provider_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """测试搜索服务商连接。"""
    provider = get_search_provider(provider_type)
    return provider.test_connection(config)
