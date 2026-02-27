"""概念历史记录应用层服务。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from backend.domain.ports import ConceptHistoryRepositoryPort

_concept_history_app_service: "ConceptHistoryApplicationService | None" = None


class ConceptHistoryApplicationService:
    """封装概念历史记录的应用层编排。"""

    def __init__(self, repository: ConceptHistoryRepositoryPort) -> None:
        self._repository = repository

    def list_history(self, page: int = 1, page_size: int = 20, status: Optional[str] = None) -> Dict[str, Any]:
        """获取概念历史记录分页列表。"""
        return self._repository.list_records(page=page, page_size=page_size, status=status)

    def get_history_detail(self, record_id: str) -> Optional[Dict[str, Any]]:
        """获取单条概念历史记录详情。"""
        return self._repository.get_record(record_id)

    def delete_history(self, record_id: str) -> bool:
        """删除单条概念历史记录。"""
        return self._repository.delete_record(record_id)

    def repair_history(self) -> Dict[str, Any]:
        """修复概念历史记录中的图片元数据。"""
        return self._repository.repair_all_records()


def get_concept_history_application_service() -> ConceptHistoryApplicationService:
    """获取概念历史记录应用层服务（单例）。"""
    global _concept_history_app_service
    if _concept_history_app_service is None:
        from backend.infrastructure.services.concept_history import get_concept_history_service

        _concept_history_app_service = ConceptHistoryApplicationService(
            repository=get_concept_history_service(),
        )
    return _concept_history_app_service
