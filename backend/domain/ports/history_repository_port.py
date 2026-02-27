"""历史记录仓储端口协议。"""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol


class HistoryRepositoryPort(Protocol):
    """图文历史记录仓储端口。"""

    def create_record(
        self,
        topic: str,
        outline: Dict[str, Any],
        task_id: Optional[str] = None,
        content: Optional[Dict[str, Any]] = None,
    ) -> str:
        ...

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        ...

    def record_exists(self, record_id: str) -> bool:
        ...

    def update_record(
        self,
        record_id: str,
        outline: Optional[Dict[str, Any]] = None,
        images: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        thumbnail: Optional[str] = None,
        content: Optional[Dict[str, Any]] = None,
    ) -> bool:
        ...

    def delete_record(self, record_id: str) -> bool:
        ...

    def list_records(self, page: int = 1, page_size: int = 20, status: Optional[str] = None) -> Dict[str, Any]:
        ...

    def search_records(self, keyword: str) -> list[Dict[str, Any]]:
        ...

    def get_statistics(self) -> Dict[str, Any]:
        ...


class ConceptHistoryRepositoryPort(Protocol):
    """概念可视化历史记录仓储端口。"""

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


class ConceptRepositoryPort(ConceptHistoryRepositoryPort, Protocol):
    """概念记录仓储端口（与概念历史记录仓储保持同一契约）。"""

    ...
