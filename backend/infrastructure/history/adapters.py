"""历史记录存储适配器。"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Protocol

STORAGE_MODE_LOCAL = "local"
STORAGE_MODE_SUPABASE = "supabase"


class HistoryStorageAdapterProtocol(Protocol):
    """历史记录存储适配器协议。"""

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

    def search_records(self, keyword: str) -> List[Dict[str, Any]]:
        ...

    def get_statistics(self) -> Dict[str, Any]:
        ...


class LocalHistoryStorageAdapter:
    """本地文件历史存储适配器。"""

    def __init__(self, service: Any) -> None:
        self.service = service

    def create_record(
        self,
        topic: str,
        outline: Dict[str, Any],
        task_id: Optional[str] = None,
        content: Optional[Dict[str, Any]] = None,
    ) -> str:
        return self.service._create_record_local(topic, outline, task_id, content)

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        return self.service._get_record_local(record_id)

    def record_exists(self, record_id: str) -> bool:
        record_path = self.service._get_record_path(record_id)
        return os.path.exists(record_path)

    def update_record(
        self,
        record_id: str,
        outline: Optional[Dict[str, Any]] = None,
        images: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        thumbnail: Optional[str] = None,
        content: Optional[Dict[str, Any]] = None,
    ) -> bool:
        return self.service._update_record_local(record_id, outline, images, status, thumbnail, content)

    def delete_record(self, record_id: str) -> bool:
        return self.service._delete_record_local(record_id)

    def list_records(self, page: int = 1, page_size: int = 20, status: Optional[str] = None) -> Dict[str, Any]:
        return self.service._list_records_local(page, page_size, status)

    def search_records(self, keyword: str) -> List[Dict[str, Any]]:
        return self.service._search_records_local(keyword)

    def get_statistics(self) -> Dict[str, Any]:
        return self.service._get_statistics_local()


class SupabaseHistoryStorageAdapter:
    """Supabase 历史存储适配器。"""

    def __init__(self, service: Any) -> None:
        self.service = service

    def create_record(
        self,
        topic: str,
        outline: Dict[str, Any],
        task_id: Optional[str] = None,
        content: Optional[Dict[str, Any]] = None,
    ) -> str:
        return self.service._create_record_supabase(topic, outline, task_id, content)

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        return self.service._get_record_supabase(record_id)

    def record_exists(self, record_id: str) -> bool:
        from backend.utils.supabase_client import get_history_record as sb_get

        result = sb_get(record_id)
        return result.get("success", False)

    def update_record(
        self,
        record_id: str,
        outline: Optional[Dict[str, Any]] = None,
        images: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        thumbnail: Optional[str] = None,
        content: Optional[Dict[str, Any]] = None,
    ) -> bool:
        return self.service._update_record_supabase(record_id, outline, images, status, thumbnail, content)

    def delete_record(self, record_id: str) -> bool:
        return self.service._delete_record_supabase(record_id)

    def list_records(self, page: int = 1, page_size: int = 20, status: Optional[str] = None) -> Dict[str, Any]:
        return self.service._list_records_supabase(page, page_size, status)

    def search_records(self, keyword: str) -> List[Dict[str, Any]]:
        return self.service._search_records_supabase(keyword)

    def get_statistics(self) -> Dict[str, Any]:
        return self.service._get_statistics_supabase()


def create_history_storage_adapter(storage_mode: str, service: Any) -> HistoryStorageAdapterProtocol:
    """根据存储模式创建历史记录存储适配器。"""
    normalized_mode = (storage_mode or STORAGE_MODE_LOCAL).strip().lower()
    if normalized_mode == STORAGE_MODE_SUPABASE:
        return SupabaseHistoryStorageAdapter(service)
    return LocalHistoryStorageAdapter(service)
