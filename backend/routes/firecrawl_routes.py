"""Firecrawl 网页抓取相关 API。"""
import logging
from urllib.parse import urlparse

import requests
from flask import Blueprint, jsonify, request

from backend.config import Config
from .utils import log_error, log_request

logger = logging.getLogger(__name__)


def create_firecrawl_blueprint():
    """创建 Firecrawl 路由蓝图。"""
    bp = Blueprint('firecrawl', __name__)

    @bp.route('/firecrawl/status', methods=['GET'])
    def get_status():
        """返回 Firecrawl 启用与配置状态。"""
        try:
            config = Config.load_firecrawl_config()
            enabled = bool(config.get('enabled', False))
            has_api_key = bool((config.get('api_key') or '').strip())
            has_base_url = bool((config.get('base_url') or '').strip())

            return jsonify({
                "success": True,
                "enabled": enabled,
                "configured": has_api_key or has_base_url,
            })
        except Exception as e:
            log_error('/firecrawl/status', e)
            return jsonify({"success": False, "error": f"读取 Firecrawl 配置失败: {str(e)}"}), 500

    @bp.route('/firecrawl/scrape', methods=['POST'])
    def scrape_url():
        """抓取指定 URL 的正文（Markdown）。"""
        try:
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                data = {}
            url = (data.get('url') or '').strip()

            log_request('/firecrawl/scrape', {'url': url})

            if not url:
                return jsonify({"success": False, "error": "参数错误：url 不能为空"}), 400
            if not _is_valid_http_url(url):
                return jsonify({"success": False, "error": "参数错误：url 必须是有效的 http/https 地址"}), 400

            config = Config.get_firecrawl_config()
            if not config:
                return jsonify({
                    "success": False,
                    "error": "Firecrawl 未启用。请在 firecrawl_config.yaml 中设置 enabled: true"
                }), 400

            result = _scrape_with_firecrawl(url, config)
            return jsonify(result), 200 if result.get('success') else 400

        except Exception as e:
            log_error('/firecrawl/scrape', e)
            return jsonify({"success": False, "error": f"抓取网页失败: {str(e)}"}), 500

    return bp


def _is_valid_http_url(url: str) -> bool:
    """校验 URL 是否是 http/https。"""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ('http', 'https') and bool(parsed.netloc)
    except Exception:
        return False


def _scrape_with_firecrawl(url: str, config: dict) -> dict:
    """调用 Firecrawl API 抓取网页。"""
    base_url = (config.get('base_url') or 'https://api.firecrawl.dev').rstrip('/')
    api_url = f"{base_url}/v1/scrape"

    headers = {"Content-Type": "application/json"}
    api_key = (config.get('api_key') or '').strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "url": url,
        "formats": ["markdown"],
    }

    logger.info(f"🌐 Firecrawl 开始抓取: {url}")

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
    except requests.exceptions.Timeout:
        return {"success": False, "error": "抓取超时，请稍后重试"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": f"无法连接到 Firecrawl 服务: {base_url}"}

    if response.status_code != 200:
        if response.status_code == 401:
            return {"success": False, "error": "Firecrawl API Key 无效或未提供"}
        if response.status_code == 402:
            return {"success": False, "error": "Firecrawl API 配额已用尽"}
        return {
            "success": False,
            "error": f"Firecrawl 请求失败: HTTP {response.status_code}"
        }

    result = response.json()
    data = result.get('data') or {}
    content = data.get('markdown') or ''
    metadata = data.get('metadata') or {}
    title = metadata.get('title') or metadata.get('ogTitle') or '未命名网页'

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
        }
    }
