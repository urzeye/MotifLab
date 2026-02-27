"""历史记录应用层服务。"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from backend.services.history import HistoryService, get_history_service

_history_application_service: "HistoryApplicationService | None" = None


class HistoryApplicationService:
    """封装历史记录相关的应用层编排。"""

    def __init__(self, history_service: HistoryService) -> None:
        self._history_service = history_service

    def create_record(
        self,
        topic: str,
        outline: Dict[str, Any],
        task_id: Optional[str] = None,
        content: Optional[Dict[str, Any]] = None,
    ) -> str:
        """创建历史记录。"""
        return self._history_service.create_record(topic, outline, task_id, content)

    def list_records(self, page: int = 1, page_size: int = 20, status: Optional[str] = None) -> Dict[str, Any]:
        """分页查询历史记录。"""
        return self._history_service.list_records(page, page_size, status)

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """获取历史记录详情。"""
        return self._history_service.get_record(record_id)

    def record_exists(self, record_id: str) -> bool:
        """检查历史记录是否存在。"""
        return self._history_service.record_exists(record_id)

    def update_record(
        self,
        record_id: str,
        outline: Optional[Dict[str, Any]] = None,
        images: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        thumbnail: Optional[str] = None,
        content: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """更新历史记录。"""
        return self._history_service.update_record(
            record_id,
            outline=outline,
            images=images,
            status=status,
            thumbnail=thumbnail,
            content=content,
        )

    def delete_record(self, record_id: str) -> bool:
        """删除历史记录。"""
        return self._history_service.delete_record(record_id)

    def search_records(self, keyword: str) -> list[Dict[str, Any]]:
        """按关键词搜索历史记录。"""
        return self._history_service.search_records(keyword)

    def get_statistics(self) -> Dict[str, Any]:
        """获取历史记录统计。"""
        return self._history_service.get_statistics()

    def scan_and_sync_task_images(self, task_id: str) -> Dict[str, Any]:
        """扫描并同步单个任务图片。"""
        return self._history_service.scan_and_sync_task_images(task_id)

    def scan_all_tasks(self) -> Dict[str, Any]:
        """扫描并同步全部任务图片。"""
        return self._history_service.scan_all_tasks()

    def is_supabase_mode(self) -> bool:
        """返回是否使用 Supabase 模式。"""
        return self._history_service.is_supabase_mode

    def get_task_dir(self, task_id: str) -> str:
        """返回本地模式下任务目录路径。"""
        return os.path.join(self._history_service.history_dir, task_id)


def get_history_application_service() -> HistoryApplicationService:
    """获取历史记录应用层服务（单例）。"""
    global _history_application_service
    if _history_application_service is None:
        _history_application_service = HistoryApplicationService(get_history_service())
    return _history_application_service
