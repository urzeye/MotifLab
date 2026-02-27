"""概念历史记录存储适配器。"""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol

STORAGE_MODE_LOCAL = "local"
STORAGE_MODE_SUPABASE = "supabase"


class ConceptHistoryStorageAdapterProtocol(Protocol):
    """概念历史存储适配器协议。"""

    def create_record(
        self,
        title: str,
        article: str,
        task_id: str,
        style: Optional[str] = None,
    ) -> str:
        ...

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        ...

    def update_record(
        self,
        record_id: str,
        title: Optional[str] = None,
        status: Optional[str] = None,
        thumbnail: Optional[str] = None,
        image_count: Optional[int] = None,
        pipeline_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        ...

    def delete_record(self, record_id: str) -> bool:
        ...

    def list_records(self, page: int = 1, page_size: int = 20, status: Optional[str] = None) -> Dict[str, Any]:
        ...

    def get_record_by_task_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        ...

    def repair_record_images(self, record_id: str) -> bool:
        ...

    def repair_all_records(self) -> Dict[str, Any]:
        ...


class LocalConceptHistoryStorageAdapter:
    """本地概念历史存储适配器。"""

    def __init__(self, service: Any) -> None:
        self.service = service

    def create_record(
        self,
        title: str,
        article: str,
        task_id: str,
        style: Optional[str] = None,
    ) -> str:
        return self.service._create_record_local(title, article, task_id, style)

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        return self.service._get_record_local(record_id)

    def update_record(
        self,
        record_id: str,
        title: Optional[str] = None,
        status: Optional[str] = None,
        thumbnail: Optional[str] = None,
        image_count: Optional[int] = None,
        pipeline_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        return self.service._update_record_local(
            record_id,
            title=title,
            status=status,
            thumbnail=thumbnail,
            image_count=image_count,
            pipeline_data=pipeline_data,
        )

    def delete_record(self, record_id: str) -> bool:
        return self.service._delete_record_local(record_id)

    def list_records(self, page: int = 1, page_size: int = 20, status: Optional[str] = None) -> Dict[str, Any]:
        return self.service._list_records_local(page, page_size, status)

    def get_record_by_task_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.service._get_record_by_task_id_local(task_id)

    def repair_record_images(self, record_id: str) -> bool:
        return self.service._repair_record_images_local(record_id)

    def repair_all_records(self) -> Dict[str, Any]:
        return self.service._repair_all_records_local()


def create_concept_history_storage_adapter(
    storage_mode: str,
    service: Any,
) -> ConceptHistoryStorageAdapterProtocol:
    """根据存储模式创建概念历史存储适配器。"""
    normalized_mode = (storage_mode or STORAGE_MODE_LOCAL).strip().lower()
    if normalized_mode in {STORAGE_MODE_LOCAL, STORAGE_MODE_SUPABASE}:
        # 目前仅落地本地实现，保留 supabase 扩展口
        return LocalConceptHistoryStorageAdapter(service)
    return LocalConceptHistoryStorageAdapter(service)
