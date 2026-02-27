"""搜索抓取相关 API。"""

import logging
from typing import Any, Optional

from flask import Blueprint, current_app, request

from backend.application.services import get_search_application_service
from backend.interfaces.http import json_response

from .utils import log_error, log_request

logger = logging.getLogger(__name__)
search_application_service = get_search_application_service()


def create_search_blueprint():
    """创建搜索路由蓝图。"""
    bp = Blueprint("search", __name__)

    @bp.route("/search/status", methods=["GET"])
    def get_search_status():
        """返回搜索服务启用与配置状态。"""
        try:
            provider = (request.args.get("provider") or "").strip()
            response = _build_provider_status(provider_name=provider or None)
            return json_response({"success": True, **response}, 200)
        except Exception as e:
            log_error("/search/status", e)
            return json_response({"success": False, "error": f"读取搜索配置失败: {str(e)}"}, 500)

    @bp.route("/search/scrape", methods=["POST"])
    def search_scrape_url():
        """按指定搜索服务商抓取 URL 正文。"""
        return _handle_scrape_request(route="/search/scrape", provider_override=None)

    return bp


def _build_provider_status(provider_name: Optional[str] = None) -> dict[str, Any]:
    return search_application_service.build_provider_status(provider_name)


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
            return json_response({"success": False, "error": "参数错误：url 不能为空"}, 400)
        if not search_application_service.is_valid_http_url(url):
            return json_response({"success": False, "error": "参数错误：url 必须是有效的 http/https 地址"}, 400)

        try:
            search_application_service.get_search_provider_config(provider_name, require_enabled=True)
        except ValueError as config_error:
            error_text = str(config_error)
            if "未启用" in error_text:
                provider_for_msg = provider_name or search_application_service.build_provider_status().get("provider")
                return json_response({
                    "success": False,
                    "error": f"搜索服务商 [{provider_for_msg}] 未启用。请在系统设置中启用并配置。",
                }, 400)
            return json_response({"success": False, "error": error_text}, 400)

        registry = _resolve_search_provider_registry()
        result = search_application_service.scrape_url(url, provider_name=provider_name, registry=registry)
        return json_response(result, 200 if result.get("success") else 400)

    except Exception as e:
        log_error(route, e)
        return json_response({"success": False, "error": f"抓取网页失败: {str(e)}"}, 500)


def _resolve_search_provider_registry():
    """解析搜索服务商注册表。"""
    try:
        container = current_app.extensions.get("backend_container")
        if container:
            return container.get_adapter("search_provider_registry")
    except Exception:
        logger.debug("容器搜索注册表不可用，回退默认搜索服务商实现")
    return None
