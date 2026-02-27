"""搜索抓取相关 API。"""

import logging
from typing import Any, Dict, Optional

from flask import Blueprint, jsonify, request

from backend.config import get_config_service
from backend.services.search_service import is_valid_http_url, scrape_with_provider
from .utils import log_error, log_request

logger = logging.getLogger(__name__)
config_service = get_config_service()


def create_search_blueprint():
    """创建搜索路由蓝图。"""
    bp = Blueprint("search", __name__)

    @bp.route("/search/status", methods=["GET"])
    def get_search_status():
        """返回搜索服务启用与配置状态。"""
        try:
            provider = (request.args.get("provider") or "").strip()
            response = _build_provider_status(provider_name=provider or None)
            return jsonify({"success": True, **response})
        except Exception as e:
            log_error("/search/status", e)
            return jsonify({"success": False, "error": f"读取搜索配置失败: {str(e)}"}), 500

    @bp.route("/search/scrape", methods=["POST"])
    def search_scrape_url():
        """按指定搜索服务商抓取 URL 正文。"""
        return _handle_scrape_request(route="/search/scrape", provider_override=None)

    return bp


def _build_provider_status(provider_name: Optional[str] = None) -> Dict[str, Any]:
    provider_name = provider_name or config_service.get_active_search_provider()
    search_config = config_service.load_search_providers_config()
    providers = search_config.get("providers") or {}
    provider_config = providers.get(provider_name) or {}

    has_api_key = bool((provider_config.get("api_key") or "").strip())
    has_base_url = bool((provider_config.get("base_url") or "").strip())
    return {
        "active_provider": search_config.get("active_provider"),
        "provider": provider_name,
        "enabled": bool(provider_config.get("enabled", False)),
        "configured": has_api_key or has_base_url,
    }


def _handle_scrape_request(route: str, provider_override: Optional[str]):
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            data = {}

        url = (data.get("url") or "").strip()
        body_provider = (data.get("provider") or "").strip().lower()
        provider_name = provider_override or body_provider or None

        log_request(route, {"url": url, "provider": provider_name})

        if not url:
            return jsonify({"success": False, "error": "参数错误：url 不能为空"}), 400
        if not is_valid_http_url(url):
            return jsonify({"success": False, "error": "参数错误：url 必须是有效的 http/https 地址"}), 400

        try:
            provider_config = config_service.get_search_provider_config(provider_name, require_enabled=True)
        except ValueError as config_error:
            error_text = str(config_error)
            if "未启用" in error_text:
                provider_for_msg = provider_name or config_service.get_active_search_provider()
                return jsonify({
                    "success": False,
                    "error": f"搜索服务商 [{provider_for_msg}] 未启用。请在系统设置中启用并配置。",
                }), 400
            return jsonify({"success": False, "error": error_text}), 400

        result = scrape_with_provider(url, provider_config)
        return jsonify(result), 200 if result.get("success") else 400

    except Exception as e:
        log_error(route, e)
        return jsonify({"success": False, "error": f"抓取网页失败: {str(e)}"}), 500
