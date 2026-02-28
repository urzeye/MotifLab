"""发布应用层服务。"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from backend.domain.ports import PublishRepositoryPort
from backend.infrastructure.persistence import get_publish_repository
from backend.infrastructure.services.publish import PublishService, publish_service

_publish_application_service: "PublishApplicationService | None" = None


class PublishApplicationService:
    """封装发布能力的应用层编排，屏蔽异步执行细节。"""

    def __init__(
        self,
        service: PublishService,
        publish_repository: Optional[PublishRepositoryPort] = None,
    ) -> None:
        self._service = service
        self._publish_repository = publish_repository

    @staticmethod
    def _run_async(coro):
        """在独立事件循环中执行协程，避免污染现有循环状态。"""
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    def get_mcp_status(self) -> Dict[str, Any]:
        """获取 MCP 服务状态。"""
        return self._run_async(self._service.get_mcp_status())

    def install_mcp_binary(self) -> Dict[str, Any]:
        """安装 MCP 二进制。"""
        return self._run_async(self._service.install_mcp_binary())

    def check_login(self) -> Dict[str, Any]:
        """检查小红书登录状态。"""
        return self._run_async(self._service.check_login())

    def open_login_page(self) -> Dict[str, Any]:
        """打开小红书登录页。"""
        return self._run_async(self._service.open_login_page())

    def publish(
        self,
        title: str,
        content: str,
        images: List[str],
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """发布图文内容。"""
        record_id = self._create_publish_record(
            title=title,
            content=content,
            images=images,
            tags=tags,
            status="pending",
            message="发布任务已提交",
        )
        try:
            result = self._run_async(
                self._service.publish(
                    title=title,
                    content=content,
                    images=images,
                    tags=tags,
                )
            )
            self._update_publish_record(
                record_id,
                status="success" if result.get("success") else "failed",
                message=str(result.get("message") or result.get("error") or ""),
                post_url=result.get("post_url"),
            )
            if record_id is not None:
                result["publish_record_id"] = record_id
            return result
        except Exception as exc:
            self._update_publish_record(record_id, status="failed", message=str(exc))
            raise

    def publish_with_video(
        self,
        title: str,
        content: str,
        video_path: str,
        cover_image: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """发布视频内容。"""
        record_id = self._create_publish_record(
            title=title,
            content=content,
            images=[video_path] if video_path else [],
            tags=tags,
            status="pending",
            message="视频发布任务已提交",
        )
        try:
            result = self._run_async(
                self._service.publish_with_video(
                    title=title,
                    content=content,
                    video_path=video_path,
                    cover_image=cover_image,
                    tags=tags,
                )
            )
            self._update_publish_record(
                record_id,
                status="success" if result.get("success") else "failed",
                message=str(result.get("message") or result.get("error") or ""),
                post_url=result.get("post_url"),
            )
            if record_id is not None:
                result["publish_record_id"] = record_id
            return result
        except Exception as exc:
            self._update_publish_record(record_id, status="failed", message=str(exc))
            raise

    def list_posts(self, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """分页获取帖子列表。"""
        return self._run_async(self._service.list_my_posts(page=page, limit=limit))

    def search_posts(self, keyword: str, page: int = 1) -> Dict[str, Any]:
        """按关键词搜索帖子。"""
        return self._run_async(self._service.search_posts(keyword=keyword, page=page))

    def list_publish_records(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """分页查询本地发布审计记录。"""
        if self._publish_repository is None:
            return {"records": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}
        return self._publish_repository.list_records(page=page, page_size=page_size, status=status)

    def _create_publish_record(
        self,
        *,
        title: str,
        content: str,
        images: List[str],
        tags: Optional[List[str]],
        status: str,
        message: str,
    ) -> Optional[int]:
        if self._publish_repository is None:
            return None
        try:
            return self._publish_repository.create_record(
                title=title,
                content=content,
                images=images,
                tags=tags,
                status=status,
                message=message,
            )
        except Exception:
            return None

    def _update_publish_record(
        self,
        record_id: Optional[int],
        *,
        status: Optional[str] = None,
        message: Optional[str] = None,
        post_url: Optional[str] = None,
    ) -> None:
        if self._publish_repository is None or record_id is None:
            return
        try:
            self._publish_repository.update_record(
                record_id,
                status=status,
                message=message,
                post_url=post_url,
            )
        except Exception:
            return


def get_publish_application_service() -> PublishApplicationService:
    """获取发布应用层服务（单例）。"""
    global _publish_application_service
    if _publish_application_service is None:
        _publish_application_service = PublishApplicationService(
            publish_service,
            publish_repository=get_publish_repository(),
        )
    return _publish_application_service
