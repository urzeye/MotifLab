"""模板市集 API 路由。"""

from __future__ import annotations

from flask import Blueprint, request

from backend.application.services import get_template_application_service
from backend.interfaces.http import json_response


def create_template_blueprint() -> Blueprint:
    """创建模板路由蓝图。"""
    template_bp = Blueprint("template", __name__)
    template_application_service = get_template_application_service()

    @template_bp.route("/templates", methods=["GET"])
    def list_templates():
        q = request.args.get("q", "").strip()
        category = request.args.get("category", "").strip()
        limit_raw = request.args.get("limit", "").strip()

        limit = None
        if limit_raw:
            try:
                limit = int(limit_raw)
            except ValueError:
                return json_response({"success": False, "error": "limit 必须是整数"}, 400)

        templates, total = template_application_service.list_templates(q=q, category=category, limit=limit)

        return json_response({
            "success": True,
            "templates": templates,
            "total": total,
            "q": q,
            "category": category
        }, 200)

    @template_bp.route("/templates/categories", methods=["GET"])
    def list_categories():
        categories = template_application_service.list_categories()
        return json_response({
            "success": True,
            "categories": categories
        }, 200)

    @template_bp.route("/templates/<template_id>", methods=["GET"])
    def get_template(template_id: str):
        template = template_application_service.get_template(template_id)
        if template is None:
            return json_response({
                "success": False,
                "error": f"模板不存在: {template_id}"
            }, 404)

        return json_response({
            "success": True,
            "template": template
        }, 200)

    return template_bp
