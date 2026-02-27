"""图片任务仓储端口协议。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol


class ImageJobRepositoryPort(Protocol):
    """异步图片任务仓储端口。"""

    def create_job(
        self,
        payload: Dict[str, Any],
        *,
        status: str = "queued",
    ) -> str:
        """创建图片任务并返回任务 ID。"""
        ...

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取图片任务详情。"""
        ...

    def list_jobs(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """分页查询图片任务。"""
        ...

    def update_job(
        self,
        job_id: str,
        fields: Dict[str, Any],
    ) -> bool:
        """更新图片任务字段。"""
        ...

    def mark_cancel_requested(self, job_id: str) -> bool:
        """标记任务为已请求取消。"""
        ...

    def upsert_job_item(
        self,
        job_id: str,
        page_index: int,
        fields: Dict[str, Any],
    ) -> bool:
        """创建或更新任务分页条目。"""
        ...

    def list_job_items(self, job_id: str) -> List[Dict[str, Any]]:
        """获取任务分页条目列表。"""
        ...
