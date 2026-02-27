"""模板应用层服务。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from backend.infrastructure.services.template import TemplateService, get_template_service

_template_application_service: "TemplateApplicationService | None" = None


class TemplateApplicationService:
    """封装模板查询相关用例。"""

    def __init__(self, template_service: TemplateService) -> None:
        self._template_service = template_service

    def list_templates(self, q: str = "", category: str = "", limit: Optional[int] = None) -> Tuple[List[Dict[str, Any]], int]:
        """分页（或限量）查询模板。"""
        return self._template_service.list_templates(q=q, category=category, limit=limit)

    def list_categories(self) -> List[str]:
        """获取模板分类列表。"""
        return self._template_service.list_categories()

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """获取单个模板详情。"""
        return self._template_service.get_template(template_id)


def get_template_application_service() -> TemplateApplicationService:
    """获取模板应用层服务（单例）。"""
    global _template_application_service
    if _template_application_service is None:
        _template_application_service = TemplateApplicationService(get_template_service())
    return _template_application_service
