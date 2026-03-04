"""大纲生成应用层服务。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.infrastructure.services.outline import OutlineService, get_outline_service

_outline_application_service: "OutlineApplicationService | None" = None


class OutlineApplicationService:
    """封装大纲相关用例编排。"""

    def __init__(self, outline_service: OutlineService) -> None:
        self._outline_service = outline_service

    def generate_outline(
        self,
        topic: str,
        images: Optional[List[bytes]] = None,
        source_content: Optional[str] = None,
        template_ref: Optional[Dict[str, Any]] = None,
        enable_search: bool = False,
        search_provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """生成大纲。"""
        return self._outline_service.generate_outline(
            topic=topic,
            images=images,
            source_content=source_content,
            template_ref=template_ref,
            enable_search=enable_search,
            search_provider=search_provider,
        )

    def edit_outline_with_suggestions(
        self,
        topic: str,
        current_outline: str = "",
        current_pages: Optional[List[Dict[str, Any]]] = None,
        revision_request: str = "",
        mode: str = "revise",
        template_ref: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """编辑大纲并生成每页建议。"""
        return self._outline_service.edit_outline_with_suggestions(
            topic=topic,
            current_outline=current_outline,
            current_pages=current_pages or [],
            revision_request=revision_request,
            mode=mode,
            template_ref=template_ref,
        )


def get_outline_application_service() -> OutlineApplicationService:
    """获取大纲应用层服务（单例）。"""
    global _outline_application_service
    if _outline_application_service is None:
        _outline_application_service = OutlineApplicationService(get_outline_service())
    return _outline_application_service
