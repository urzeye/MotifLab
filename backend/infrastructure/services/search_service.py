"""搜索抓取服务抽象（支持 Firecrawl / Exa / Tavily / Perplexity / Bing）。"""

from __future__ import annotations

import html
import logging
import re
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning

from backend.domain.ports import SearchProviderPort

logger = logging.getLogger(__name__)

urllib3.disable_warnings(InsecureRequestWarning)

DEFAULT_FIRECRAWL_BASE_URL = "https://api.firecrawl.dev"
DEFAULT_EXA_BASE_URL = "https://api.exa.ai"
DEFAULT_TAVILY_BASE_URL = "https://api.tavily.com"
DEFAULT_PERPLEXITY_BASE_URL = "https://api.perplexity.ai"
DEFAULT_BING_BASE_URL = "https://www.bing.com"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    )
}


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


def _clean_html_to_text(raw_html: str) -> str:
    """将 HTML 简单清洗为可读文本。"""
    text = raw_html or ""
    # 去掉 script/style 等无关标签
    text = re.sub(r"(?is)<script\b[^>]*>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style\b[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?is)<noscript\b[^>]*>.*?</noscript>", " ", text)
    # 标签转换为换行/空格，降低连词问题
    text = re.sub(r"(?i)</p>|</div>|</li>|</h\d>|<br\s*/?>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def _extract_title_from_html(raw_html: str) -> str:
    match = re.search(r"(?is)<title[^>]*>(.*?)</title>", raw_html or "")
    if not match:
        return ""
    title = html.unescape(re.sub(r"(?s)<[^>]+>", " ", match.group(1))).strip()
    return re.sub(r"\s+", " ", title)


def _fetch_page_content(url: str, timeout: int = 20) -> Tuple[str, str]:
    """
    直接抓取网页并提取文本。

    Returns:
        (title, content)
    """
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=timeout)
    except requests.exceptions.SSLError:
        logger.warning(f"网页证书校验失败，已回退不校验证书抓取: {url}")
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=timeout, verify=False)
    response.raise_for_status()

    content_type = (response.headers.get("Content-Type") or "").lower()
    response.encoding = response.encoding or response.apparent_encoding or "utf-8"

    body = response.text or ""
    if "html" in content_type or "<html" in body.lower():
        title = _extract_title_from_html(body)
        content = _clean_html_to_text(body)
    else:
        title = ""
        content = _normalize_text(body)

    return title.strip(), content.strip()


def _build_success(url: str, title: str, content: str) -> Dict[str, Any]:
    return {
        "success": True,
        "data": {
            "title": title or "未命名网页",
            "content": content,
            "word_count": len(content),
            "url": url,
        },
    }


def _resolve_timeout_seconds(config: Dict[str, Any], default: int = 20) -> int:
    try:
        parsed = int(config.get("timeout_seconds", default))
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(60, parsed))


def _resolve_max_results(config: Dict[str, Any], default: int = 5) -> int:
    try:
        parsed = int(config.get("max_results", default))
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(20, parsed))


class BaseSearchProvider(SearchProviderPort):
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
        timeout_seconds = _resolve_timeout_seconds(config)

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {"url": url, "formats": ["markdown"]}
        endpoints = [f"{base_url}/v2/scrape", f"{base_url}/v1/scrape"]
        errors: list[str] = []

        logger.info(f"🌐 Firecrawl 开始抓取: {url}")

        for index, api_url in enumerate(endpoints):
            try:
                response = requests.post(api_url, headers=headers, json=payload, timeout=timeout_seconds)
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
        timeout_seconds = _resolve_timeout_seconds(config)

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
            response = requests.post(api_url, headers=headers, json=payload, timeout=timeout_seconds)
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
        return _build_success(url, title, content)


class TavilySearchProvider(BaseSearchProvider):
    """Tavily 抓取实现（/extract）。"""

    provider_type = "tavily"

    def scrape(self, url: str, config: Dict[str, Any]) -> Dict[str, Any]:
        base_url = (config.get("base_url") or DEFAULT_TAVILY_BASE_URL).rstrip("/")
        api_key = (config.get("api_key") or "").strip()
        timeout_seconds = _resolve_timeout_seconds(config)
        if not api_key:
            return {"success": False, "error": "Tavily API Key 未配置"}

        api_url = f"{base_url}/extract"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        payload = {
            "urls": [url],
            "extract_depth": "basic",
        }

        logger.info(f"🌐 Tavily 开始抓取: {url}")

        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=timeout_seconds)
        except requests.exceptions.Timeout:
            return {"success": False, "error": "抓取超时，请稍后重试"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": f"无法连接到 Tavily 服务: {base_url}"}

        if response.status_code != 200:
            if response.status_code == 401:
                return {"success": False, "error": "Tavily API Key 无效或未提供"}
            if response.status_code == 402:
                return {"success": False, "error": "Tavily API 配额已用尽"}
            if response.status_code == 429:
                return {"success": False, "error": "Tavily 请求过于频繁，请稍后重试"}
            return {
                "success": False,
                "error": _extract_error_message(response, f"Tavily 请求失败: HTTP {response.status_code}"),
            }

        try:
            payload_json = response.json()
        except Exception:
            return {"success": False, "error": "Tavily 返回了无法解析的响应"}

        results = payload_json.get("results") if isinstance(payload_json, dict) else None
        first = results[0] if isinstance(results, list) and results and isinstance(results[0], dict) else {}

        title = _normalize_text(first.get("title")) or "未命名网页"
        content = (
            _normalize_text(first.get("raw_content"))
            or _normalize_text(first.get("content"))
            or _normalize_text(first.get("summary"))
        )

        if not content:
            # Tavily 结果为空时，回退到直接抓取 URL
            try:
                direct_title, direct_content = _fetch_page_content(url, timeout=timeout_seconds)
            except Exception:
                direct_title, direct_content = "", ""
            title = direct_title or title
            content = direct_content or content

        if not content:
            return {"success": False, "error": "Tavily 抓取成功但未提取到正文内容"}

        logger.info(f"✅ Tavily 抓取完成: title={title[:60]}..., chars={len(content)}")
        return _build_success(url, title, content)


class PerplexitySearchProvider(BaseSearchProvider):
    """Perplexity 搜索抓取实现（/search）。"""

    provider_type = "perplexity"

    def scrape(self, url: str, config: Dict[str, Any]) -> Dict[str, Any]:
        base_url = (config.get("base_url") or DEFAULT_PERPLEXITY_BASE_URL).rstrip("/")
        api_key = (config.get("api_key") or "").strip()
        model = (config.get("model") or "sonar").strip()
        timeout_seconds = _resolve_timeout_seconds(config)
        max_results = _resolve_max_results(config)
        if not api_key:
            return {"success": False, "error": "Perplexity API Key 未配置"}

        api_url = f"{base_url}/search"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        payload = {
            "query": url,
            "max_results": max_results,
            "model": model,
        }

        logger.info(f"🌐 Perplexity 开始抓取: {url}")

        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=timeout_seconds)
        except requests.exceptions.Timeout:
            return {"success": False, "error": "抓取超时，请稍后重试"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": f"无法连接到 Perplexity 服务: {base_url}"}

        if response.status_code != 200:
            if response.status_code == 401:
                return {"success": False, "error": "Perplexity API Key 无效或未提供"}
            if response.status_code == 402:
                return {"success": False, "error": "Perplexity API 配额已用尽"}
            if response.status_code == 429:
                return {"success": False, "error": "Perplexity 请求过于频繁，请稍后重试"}
            return {
                "success": False,
                "error": _extract_error_message(response, f"Perplexity 请求失败: HTTP {response.status_code}"),
            }

        try:
            payload_json = response.json()
        except Exception:
            return {"success": False, "error": "Perplexity 返回了无法解析的响应"}

        results = payload_json.get("results") if isinstance(payload_json, dict) else None
        first = results[0] if isinstance(results, list) and results and isinstance(results[0], dict) else {}

        result_url = _normalize_text(first.get("url")) or url
        title = _normalize_text(first.get("title")) or "未命名网页"
        snippet = _normalize_text(first.get("snippet")) or _normalize_text(first.get("content"))

        # 优先抓取命中页面正文，snippet 作为兜底
        direct_title, direct_content = "", ""
        try:
            direct_title, direct_content = _fetch_page_content(result_url, timeout=timeout_seconds)
        except Exception:
            pass

        title = direct_title or title
        content = direct_content or snippet
        if not content and result_url != url:
            try:
                title2, content2 = _fetch_page_content(url, timeout=timeout_seconds)
                title = title or title2
                content = content or content2
            except Exception:
                pass

        if not content:
            return {"success": False, "error": "Perplexity 抓取成功但未提取到正文内容"}

        logger.info(f"✅ Perplexity 抓取完成: title={title[:60]}..., chars={len(content)}")
        return _build_success(result_url, title, content)


class BingSearchProvider(BaseSearchProvider):
    """
    Bing 默认抓取实现。

    无需 API Key：通过 Bing RSS 搜索定位结果，再抓取目标网页正文。
    """

    provider_type = "bing"

    def scrape(self, url: str, config: Dict[str, Any]) -> Dict[str, Any]:
        base_url = (config.get("base_url") or DEFAULT_BING_BASE_URL).rstrip("/")
        search_url = f"{base_url}/search"
        timeout_seconds = _resolve_timeout_seconds(config)

        logger.info(f"🌐 Bing 开始抓取: {url}")

        # 0) 优先直接抓取目标 URL（可确保与输入地址一致）
        try:
            direct_title, direct_content = _fetch_page_content(url, timeout=timeout_seconds)
            if direct_content:
                logger.info(f"✅ Bing 直连抓取完成: title={direct_title[:60]}..., chars={len(direct_content)}")
                return _build_success(url, direct_title or "未命名网页", direct_content)
        except Exception:
            pass

        # 1) 先通过 Bing RSS 定位最可能的目标链接
        title = ""
        snippet = ""
        target_url = url
        try:
            response = requests.get(
                search_url,
                params={"q": url, "format": "rss"},
                headers=REQUEST_HEADERS,
                timeout=timeout_seconds,
            )
            if response.status_code == 200:
                parsed = ET.fromstring(response.text)
                first_item = parsed.find("./channel/item")
                if first_item is not None:
                    title = _normalize_text(first_item.findtext("title"))
                    link = _normalize_text(first_item.findtext("link"))
                    description = _normalize_text(first_item.findtext("description"))
                    if link and is_valid_http_url(link):
                        target_url = link
                    snippet = description
        except Exception as e:
            logger.warning(f"Bing RSS 检索失败，回退直接抓取: {e}")

        # 2) 抓取目标网页正文
        direct_title, direct_content = "", ""
        try:
            direct_title, direct_content = _fetch_page_content(target_url, timeout=timeout_seconds)
        except Exception:
            # 回退抓取用户原始 URL
            if target_url != url:
                try:
                    direct_title, direct_content = _fetch_page_content(url, timeout=timeout_seconds)
                    target_url = url
                except Exception:
                    pass

        final_title = direct_title or title or "未命名网页"
        final_content = direct_content or snippet
        if not final_content:
            return {"success": False, "error": "Bing 抓取成功但未提取到正文内容"}

        logger.info(f"✅ Bing 抓取完成: title={final_title[:60]}..., chars={len(final_content)}")
        return _build_success(target_url, final_title, final_content)


class SearchProviderRegistry:
    """搜索服务商注册表，支持按名称动态注册与扩展。"""

    def __init__(self) -> None:
        self._providers: Dict[str, type[BaseSearchProvider]] = {}

    def register(self, provider_type: str, provider_class: type[BaseSearchProvider]) -> None:
        """注册服务商实现类。"""
        normalized = (provider_type or "").strip().lower()
        if not normalized:
            raise ValueError("provider_type 不能为空")
        if not issubclass(provider_class, BaseSearchProvider):
            raise TypeError("provider_class 必须继承 BaseSearchProvider")
        self._providers[normalized] = provider_class

    def create(self, provider_type: str) -> BaseSearchProvider:
        """创建服务商实例。"""
        normalized = (provider_type or "").strip().lower()
        provider_class = self._providers.get(normalized)
        if provider_class is None:
            raise ValueError(f"不支持的搜索服务商: {provider_type}")
        return provider_class()

    def list_types(self) -> list[str]:
        """返回已注册的服务商类型列表。"""
        return sorted(self._providers.keys())


def build_default_search_provider_registry() -> SearchProviderRegistry:
    """构建默认搜索服务商注册表。"""
    registry = SearchProviderRegistry()
    registry.register("bing", BingSearchProvider)
    registry.register("firecrawl", FirecrawlSearchProvider)
    registry.register("exa", ExaSearchProvider)
    registry.register("tavily", TavilySearchProvider)
    registry.register("perplexity", PerplexitySearchProvider)
    return registry


_search_provider_registry = build_default_search_provider_registry()


def register_search_provider(provider_type: str, provider_class: type[BaseSearchProvider]) -> None:
    """注册自定义搜索服务商实现。"""
    _search_provider_registry.register(provider_type, provider_class)


def get_search_provider(provider_type: str) -> BaseSearchProvider:
    """按 provider type 获取抓取实现。"""
    return _search_provider_registry.create(provider_type)


def scrape_with_provider(url: str, provider_config: Dict[str, Any]) -> Dict[str, Any]:
    """使用指定 provider 配置抓取网页。"""
    provider_type = (provider_config.get("type") or "").strip().lower()
    provider = get_search_provider(provider_type)
    return provider.scrape(url, provider_config)


def test_provider(provider_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """测试搜索服务商连接。"""
    provider = get_search_provider(provider_type)
    return provider.test_connection(config)
