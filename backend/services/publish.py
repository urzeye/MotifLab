"""
小红书发布服务

使用 xiaohongshu-mcp 提供的工具进行发布操作。
"""

import logging
from typing import Dict, Any, List, Optional

from backend.utils.mcp_manager import mcp_manager

logger = logging.getLogger(__name__)


class PublishService:
    """
    小红书发布服务

    封装 xiaohongshu-mcp 的发布相关功能，提供统一的接口。
    """

    def __init__(self):
        self.mcp = mcp_manager

    async def get_mcp_status(self) -> Dict[str, Any]:
        """
        获取 MCP 服务状态

        Returns:
            dict: 包含 running, url, binary_installed 等信息
        """
        return self.mcp.get_status()

    async def check_login(self) -> Dict[str, Any]:
        """
        检查小红书登录状态

        Returns:
            dict: {
                "success": bool,
                "logged_in": bool,
                "message": str,
                "user_info": dict (如果已登录)
            }
        """
        result = await self.mcp.call_tool("check_login_status")

        if not result.get("success", True):
            return {
                "success": False,
                "logged_in": False,
                "message": result.get("error", "检查登录状态失败")
            }

        # 解析 MCP 返回的结果
        logged_in = result.get("logged_in", False)
        return {
            "success": True,
            "logged_in": logged_in,
            "message": "已登录" if logged_in else "未登录，请先登录小红书",
            "user_info": result.get("user_info")
        }

    async def open_login_page(self) -> Dict[str, Any]:
        """
        打开小红书登录页面

        Returns:
            dict: 操作结果
        """
        result = await self.mcp.call_tool("open_login_page")
        return result

    async def publish(
        self,
        title: str,
        content: str,
        images: List[str],
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        发布内容到小红书

        Args:
            title: 标题（最多20字）
            content: 正文内容
            images: 图片文件路径列表
            tags: 标签列表（可选）

        Returns:
            dict: {
                "success": bool,
                "message": str,
                "post_url": str (如果发布成功)
            }
        """
        # 校验标题长度
        if len(title) > 20:
            title = title[:20]
            logger.warning(f"标题超过20字，已截断: {title}")

        # 将标签添加到内容末尾
        full_content = content
        if tags and len(tags) > 0:
            tag_str = " ".join(f"#{tag}" for tag in tags[:5])  # 最多5个标签
            full_content = f"{content}\n\n{tag_str}"

        logger.info(f"开始发布到小红书: title={title}, images={len(images)}")

        # 调用 MCP 发布工具
        result = await self.mcp.call_tool("publish_content", {
            "title": title,
            "content": full_content,
            "images": images
        })

        if not result.get("success", True):
            logger.error(f"发布失败: {result.get('error')}")
            return {
                "success": False,
                "message": result.get("error", "发布失败")
            }

        logger.info("发布成功！")
        return {
            "success": True,
            "message": "发布成功",
            "post_url": result.get("post_url")
        }

    async def publish_with_video(
        self,
        title: str,
        content: str,
        video_path: str,
        cover_image: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        发布视频到小红书

        Args:
            title: 标题
            content: 正文
            video_path: 视频文件路径
            cover_image: 封面图片路径（可选）
            tags: 标签列表

        Returns:
            dict: 发布结果
        """
        full_content = content
        if tags and len(tags) > 0:
            tag_str = " ".join(f"#{tag}" for tag in tags[:5])
            full_content = f"{content}\n\n{tag_str}"

        result = await self.mcp.call_tool("publish_with_video", {
            "title": title[:20],
            "content": full_content,
            "video_path": video_path,
            "cover_image": cover_image
        })

        return result

    async def list_my_posts(self, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """
        获取我的帖子列表

        Args:
            page: 页码
            limit: 每页数量

        Returns:
            dict: 帖子列表
        """
        result = await self.mcp.call_tool("list_feeds", {
            "page": page,
            "limit": limit
        })
        return result

    async def search_posts(self, keyword: str, page: int = 1) -> Dict[str, Any]:
        """
        搜索帖子

        Args:
            keyword: 搜索关键词
            page: 页码

        Returns:
            dict: 搜索结果
        """
        result = await self.mcp.call_tool("search_feeds", {
            "keyword": keyword,
            "page": page
        })
        return result


# 全局服务实例
publish_service = PublishService()
