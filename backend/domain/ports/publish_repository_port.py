"""发布记录仓储端口协议。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol


class PublishRepositoryPort(Protocol):
    """发布记录仓储端口。"""

    def create_record(
        self,
        title: str,
        content: str,
        images: List[str],
        tags: Optional[List[str]] = None,
        status: str = "pending",
        message: str = "",
        post_url: Optional[str] = None,
    ) -> int:
        """创建发布记录并返回自增 ID。"""
        ...

    def update_record(
        self,
        record_id: int,
        *,
        status: Optional[str] = None,
        message: Optional[str] = None,
        post_url: Optional[str] = None,
    ) -> bool:
        """更新发布记录状态。"""
        ...

    def get_record(self, record_id: int) -> Optional[Dict[str, Any]]:
        """按 ID 获取发布记录。"""
        ...

    def list_records(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """分页查询发布记录。"""
        ...
