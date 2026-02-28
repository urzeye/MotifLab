"""
小红书发布服务

使用 xiaohongshu-mcp 提供的工具进行发布操作。
"""

import logging
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import unquote, urlparse

from backend.domain.ports import PublishGatewayPort
from backend.infrastructure.gateways import get_publish_gateway

logger = logging.getLogger(__name__)


class PublishService:
    """
    小红书发布服务

    封装 xiaohongshu-mcp 的发布相关功能，提供统一的接口。
    """

    def __init__(self, gateway: PublishGatewayPort | None = None):
        self.gateway = gateway or get_publish_gateway()
        self.project_root = Path(__file__).resolve().parents[3]
        self.history_root_dir = self.project_root / "history"

    @staticmethod
    def _path_exists(path: str) -> bool:
        try:
            return bool(path) and Path(path).exists()
        except Exception:
            return False

    @staticmethod
    def _extract_api_image_ref(path: str) -> Optional[tuple[str, str]]:
        normalized = (path or "").strip().lstrip("/")
        parts = normalized.split("/")
        if len(parts) < 4:
            return None
        if parts[0] != "api" or parts[1] != "images":
            return None
        task_id = unquote(parts[2]).strip()
        filename = unquote(parts[3]).strip()
        if not task_id or not filename:
            return None
        return task_id, filename

    def _resolve_publish_image_path(self, image: Any) -> str:
        raw = unquote(str(image or "").strip())
        if not raw:
            return ""

        parsed = urlparse(raw)
        api_ref = self._extract_api_image_ref(parsed.path if parsed.path else raw)
        if api_ref:
            task_id, filename = api_ref
            image_path = self.history_root_dir / task_id / filename
            if image_path.exists():
                return str(image_path)

            # 若前端传入缩略图名，优先回退到原图。
            if filename.startswith("thumb_"):
                original_path = self.history_root_dir / task_id / filename[len("thumb_"):]
                if original_path.exists():
                    return str(original_path)
            else:
                # 原图缺失时兜底缩略图，避免直接失败。
                thumb_path = self.history_root_dir / task_id / f"thumb_{filename}"
                if thumb_path.exists():
                    logger.warning(f"发布原图缺失，回退缩略图: {raw}")
                    return str(thumb_path)

            return str(image_path)

        # 已是本地绝对路径时直接透传。
        if os.path.isabs(raw) or re.match(r"^[A-Za-z]:[\\/]", raw):
            return raw

        # 相对路径尝试按项目根目录解析。
        project_path = (self.project_root / raw).resolve()
        if project_path.exists():
            return str(project_path)
        return raw

    def _normalize_publish_images(self, images: List[str]) -> tuple[List[str], List[str]]:
        resolved: List[str] = []
        missing: List[str] = []
        for index, image in enumerate(images):
            normalized = self._resolve_publish_image_path(image)
            resolved.append(normalized)
            if not self._path_exists(normalized):
                missing.append(f"[{index}] {image} -> {normalized}")
        return resolved, missing

    @staticmethod
    def _extract_first_url(text: str) -> Optional[str]:
        if not isinstance(text, str) or not text.strip():
            return None
        matches = re.findall(r"https?://[^\s\"'<>）)]+", text)
        if not matches:
            return None

        # 优先返回小红书相关链接。
        for candidate in matches:
            lowered = candidate.lower()
            if "xiaohongshu.com" in lowered or "xhslink.com" in lowered:
                return candidate
        return matches[0]

    def _extract_post_url(self, result: Dict[str, Any]) -> Optional[str]:
        def _pick_url(value: Any) -> Optional[str]:
            if isinstance(value, str):
                candidate = value.strip()
                if candidate.startswith("http://") or candidate.startswith("https://"):
                    return candidate
                return self._extract_first_url(candidate)
            if isinstance(value, dict):
                return self._extract_post_url(value)
            return None

        key_candidates = (
            "post_url",
            "postUrl",
            "url",
            "note_url",
            "noteUrl",
            "publish_url",
            "publishUrl",
            "post_link",
            "link",
        )
        for key in key_candidates:
            if key in result:
                found = _pick_url(result.get(key))
                if found:
                    return found

        for key in ("message", "result", "content", "data"):
            if key in result:
                found = _pick_url(result.get(key))
                if found:
                    return found

        return None

    @staticmethod
    def _coerce_bool(value: Any) -> Optional[bool]:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "yes", "y", "ok", "logged_in", "loggedin", "已登录"}:
                return True
            if lowered in {"0", "false", "no", "n", "not_logged_in", "未登录"}:
                return False
        return None

    def _extract_logged_in(self, result: Dict[str, Any], message: str) -> bool:
        for key in (
            "logged_in",
            "is_logged_in",
            "isLogin",
            "is_login",
            "login",
            "loggedIn",
            "isLoggedIn",
            "has_login",
        ):
            if key in result:
                parsed = self._coerce_bool(result.get(key))
                if parsed is not None:
                    return parsed

        lowered = message.lower()
        negative_signals = (
            "未登录",
            "需要登录",
            "请先登录",
            "not logged in",
            "login required",
            "login first",
        )
        positive_signals = (
            "已登录",
            "登录成功",
            "logged in",
            "login success",
            "you are logged in",
        )
        if any(signal in lowered for signal in negative_signals):
            return False
        if any(signal in lowered for signal in positive_signals):
            return True
        return False

    @staticmethod
    def _extract_username(result: Dict[str, Any], message: str) -> Optional[str]:
        direct_username = result.get("username")
        if isinstance(direct_username, str) and direct_username.strip():
            return direct_username.strip()

        user_info = result.get("user_info")
        if isinstance(user_info, dict):
            for key in ("username", "user_name", "nickname", "nick_name"):
                value = user_info.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

        match = re.search(r"(?:用户名|账号|username)\s*[：:]\s*([^\s,，。;；]+)", message, flags=re.IGNORECASE)
        if match:
            username = match.group(1).strip()
            return username or None
        return None

    async def get_mcp_status(self) -> Dict[str, Any]:
        """
        获取 MCP 服务状态

        Returns:
            dict: 包含 running, url, binary_installed 等信息
        """
        return self.gateway.get_status()

    async def install_mcp_binary(self) -> Dict[str, Any]:
        """
        安装 xiaohongshu-mcp 二进制。

        Returns:
            dict: 安装结果
        """
        return self.gateway.install_binary()

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
        result = await self.gateway.check_login()

        if not result.get("success", True):
            return {
                "success": False,
                "logged_in": False,
                "message": result.get("error", "检查登录状态失败")
            }

        raw_message = str(result.get("message") or "").strip()
        logged_in = self._extract_logged_in(result, raw_message)
        username = self._extract_username(result, raw_message)
        user_info = result.get("user_info")
        if not isinstance(user_info, dict):
            user_info = {}
        if username and not user_info.get("username"):
            user_info["username"] = username

        return {
            "success": True,
            "logged_in": logged_in,
            "username": username,
            "message": raw_message or ("已登录" if logged_in else "未登录，请先登录小红书"),
            "user_info": user_info or None,
        }

    async def open_login_page(self) -> Dict[str, Any]:
        """
        打开小红书登录页面

        Returns:
            dict: 操作结果
        """
        return await self.gateway.open_login_page()

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

        normalized_images, missing_images = self._normalize_publish_images(images)
        if missing_images:
            details = "; ".join(missing_images[:3])
            if len(missing_images) > 3:
                details += f"; ... 共 {len(missing_images)} 张"
            logger.error(f"发布失败：图片文件不可访问: {details}")
            return {
                "success": False,
                "message": "发布失败：图片文件不可访问，请刷新结果页后重试",
                "error": f"图片文件不存在或路径无效: {details}",
            }

        logger.info(f"开始发布到小红书: title={title}, images={len(images)}")

        # 调用 MCP 发布工具
        result = await self.gateway.publish({
            "title": title,
            "content": full_content,
            "images": normalized_images
        })

        if not result.get("success", True):
            logger.error(f"发布失败: {result.get('error')}")
            return {
                "success": False,
                "message": result.get("error", "发布失败")
            }

        logger.info("发布成功！")
        post_url = self._extract_post_url(result)
        return {
            "success": True,
            "message": "发布成功",
            "post_url": post_url
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

        result = await self.gateway.publish_video({
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
        return await self.gateway.list_posts({"page": page, "limit": limit})

    async def search_posts(self, keyword: str, page: int = 1) -> Dict[str, Any]:
        """
        搜索帖子

        Args:
            keyword: 搜索关键词
            page: 页码

        Returns:
            dict: 搜索结果
        """
        return await self.gateway.search_posts({"keyword": keyword, "page": page})


# 全局服务实例
publish_service = PublishService()
