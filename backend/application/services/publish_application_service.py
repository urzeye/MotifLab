"""发布应用层服务。"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from backend.services.publish import PublishService, publish_service

_publish_application_service: "PublishApplicationService | None" = None


class PublishApplicationService:
    """封装发布能力的应用层编排，屏蔽异步执行细节。"""

    def __init__(self, service: PublishService) -> None:
        self._service = service

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
        return self._run_async(
            self._service.publish(
                title=title,
                content=content,
                images=images,
                tags=tags,
            )
        )

    def publish_with_video(
        self,
        title: str,
        content: str,
        video_path: str,
        cover_image: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """发布视频内容。"""
        return self._run_async(
            self._service.publish_with_video(
                title=title,
                content=content,
                video_path=video_path,
                cover_image=cover_image,
                tags=tags,
            )
        )

    def list_posts(self, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """分页获取帖子列表。"""
        return self._run_async(self._service.list_my_posts(page=page, limit=limit))

    def search_posts(self, keyword: str, page: int = 1) -> Dict[str, Any]:
        """按关键词搜索帖子。"""
        return self._run_async(self._service.search_posts(keyword=keyword, page=page))


def get_publish_application_service() -> PublishApplicationService:
    """获取发布应用层服务（单例）。"""
    global _publish_application_service
    if _publish_application_service is None:
        _publish_application_service = PublishApplicationService(publish_service)
    return _publish_application_service
