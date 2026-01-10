"""
发布服务

提供将内容发布到小红书等平台的功能。
使用 VibeSurf 浏览器自动化实现。
"""

import os
import time
import logging
from typing import Dict, Any, Generator, List, Optional

from backend.utils.vibesurf_client import VibeSurfClient, get_vibesurf_client

logger = logging.getLogger(__name__)


class PublishService:
    """
    发布服务类

    提供：
    - VibeSurf 状态检查
    - 小红书登录状态检查
    - 发布图文到小红书
    """

    # 小红书相关 URL
    XIAOHONGSHU_HOME = "https://www.xiaohongshu.com"
    XIAOHONGSHU_CREATOR = "https://creator.xiaohongshu.com"
    XIAOHONGSHU_PUBLISH = "https://creator.xiaohongshu.com/publish/publish"
    XIAOHONGSHU_LOGIN = "https://creator.xiaohongshu.com/login"

    def __init__(self):
        """初始化发布服务"""
        logger.debug("初始化 PublishService...")
        self.vibesurf = get_vibesurf_client()
        logger.info("PublishService 初始化完成")

    def check_vibesurf_status(self) -> Dict[str, Any]:
        """
        检查 VibeSurf 状态

        Returns:
            dict:
                - running: bool, VibeSurf 是否运行中
                - message: str, 状态消息
                - version: str, 版本信息
        """
        logger.debug("检查 VibeSurf 状态...")
        result = self.vibesurf.check_health()
        if result["running"]:
            logger.info("VibeSurf 服务运行正常")
        else:
            logger.warning(f"VibeSurf 服务未运行: {result['message']}")
        return result

    def check_login_status(self) -> Dict[str, Any]:
        """
        检查小红书登录状态

        通过访问创作者中心页面并检查是否被重定向到登录页来判断登录状态。

        Returns:
            dict:
                - logged_in: bool, 是否已登录
                - message: str, 状态消息
                - username: str, 用户名（如果已登录）
        """
        logger.info("检查小红书登录状态...")

        try:
            # 首先检查 VibeSurf 状态
            health = self.vibesurf.check_health()
            if not health["running"]:
                return {
                    "logged_in": False,
                    "message": "VibeSurf 服务未运行，请先启动 VibeSurf",
                    "vibesurf_running": False
                }

            # 导航到创作者中心
            nav_result = self.vibesurf.navigate(self.XIAOHONGSHU_CREATOR)
            if not nav_result.get("success"):
                return {
                    "logged_in": False,
                    "message": f"无法访问小红书创作者中心: {nav_result.get('error')}",
                    "vibesurf_running": True
                }

            # 等待页面加载
            self.vibesurf.wait(2)

            # 获取浏览器状态，检查当前 URL
            state_result = self.vibesurf.get_browser_state()
            if not state_result.get("success"):
                return {
                    "logged_in": False,
                    "message": "无法获取浏览器状态",
                    "vibesurf_running": True
                }

            # 检查是否在登录页面
            raw_response = state_result.get("raw_response", {})
            result_data = raw_response.get("result", {})

            # 尝试从多个可能的位置获取 URL
            current_url = ""
            if isinstance(result_data, dict):
                current_url = result_data.get("url", "")
                if not current_url:
                    # 尝试从 tabs 获取
                    tabs = result_data.get("tabs", [])
                    if tabs and len(tabs) > 0:
                        current_url = tabs[0].get("url", "")

            logger.debug(f"当前 URL: {current_url}")

            # 判断登录状态
            if "login" in current_url.lower():
                return {
                    "logged_in": False,
                    "message": "未登录小红书，请先登录",
                    "vibesurf_running": True,
                    "current_url": current_url
                }

            # 如果在创作者中心页面，说明已登录
            if "creator.xiaohongshu.com" in current_url:
                logger.info("小红书已登录")
                return {
                    "logged_in": True,
                    "message": "已登录小红书",
                    "vibesurf_running": True,
                    "current_url": current_url
                }

            # 其他情况，可能需要登录
            return {
                "logged_in": False,
                "message": "登录状态未知，请尝试手动登录",
                "vibesurf_running": True,
                "current_url": current_url
            }

        except Exception as e:
            logger.error(f"检查登录状态失败: {e}")
            return {
                "logged_in": False,
                "message": f"检查登录状态失败: {str(e)}",
                "vibesurf_running": True
            }

    def open_login_page(self) -> Dict[str, Any]:
        """
        打开小红书登录页面

        Returns:
            dict:
                - success: bool
                - message: str
        """
        logger.info("打开小红书登录页面...")

        try:
            # 检查 VibeSurf 状态
            health = self.vibesurf.check_health()
            if not health["running"]:
                return {
                    "success": False,
                    "message": "VibeSurf 服务未运行，请先启动 VibeSurf"
                }

            # 导航到登录页面
            result = self.vibesurf.navigate(self.XIAOHONGSHU_LOGIN)

            if result.get("success"):
                logger.info("已打开小红书登录页面")
                return {
                    "success": True,
                    "message": "已打开小红书登录页面，请在浏览器中完成登录"
                }
            else:
                return {
                    "success": False,
                    "message": f"打开登录页面失败: {result.get('error')}"
                }

        except Exception as e:
            logger.error(f"打开登录页面失败: {e}")
            return {
                "success": False,
                "message": f"打开登录页面失败: {str(e)}"
            }

    def publish_to_xiaohongshu(
        self,
        images: List[str],
        title: str,
        content: str,
        tags: List[str] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        发布图文到小红书

        使用 SSE 流式返回发布进度。

        发布流程：
        1. 检查 VibeSurf 和登录状态
        2. 导航到发布页面
        3. 上传图片
        4. 填写标题和正文
        5. 添加标签
        6. 点击发布
        7. 确认发布结果

        Args:
            images: 图片路径列表（本地文件路径）
            title: 标题（最多 20 个字）
            content: 正文内容
            tags: 标签列表（可选）

        Yields:
            dict: 进度事件
                - event: str, 事件类型 (progress, error, complete)
                - data: dict, 事件数据
        """
        logger.info(f"开始发布到小红书: title={title[:20]}..., images={len(images)}")

        try:
            # ==================== 1. 检查 VibeSurf 状态 ====================
            yield {
                "event": "progress",
                "data": {
                    "step": 1,
                    "total_steps": 7,
                    "status": "checking_vibesurf",
                    "message": "正在检查 VibeSurf 服务状态..."
                }
            }

            health = self.vibesurf.check_health()
            if not health["running"]:
                yield {
                    "event": "error",
                    "data": {
                        "step": 1,
                        "status": "vibesurf_not_running",
                        "message": "VibeSurf 服务未运行，请先启动 VibeSurf",
                        "recoverable": False
                    }
                }
                return

            # ==================== 2. 导航到发布页面 ====================
            yield {
                "event": "progress",
                "data": {
                    "step": 2,
                    "total_steps": 7,
                    "status": "navigating",
                    "message": "正在打开小红书发布页面..."
                }
            }

            nav_result = self.vibesurf.navigate(self.XIAOHONGSHU_PUBLISH)
            if not nav_result.get("success"):
                yield {
                    "event": "error",
                    "data": {
                        "step": 2,
                        "status": "navigation_failed",
                        "message": f"无法打开发布页面: {nav_result.get('error')}",
                        "recoverable": True
                    }
                }
                return

            # 等待页面加载
            self.vibesurf.wait(3)

            # 检查是否需要登录
            state_result = self.vibesurf.get_browser_state()
            raw_response = state_result.get("raw_response", {})
            result_data = raw_response.get("result", {})
            current_url = ""
            if isinstance(result_data, dict):
                current_url = result_data.get("url", "")

            if "login" in current_url.lower():
                yield {
                    "event": "error",
                    "data": {
                        "step": 2,
                        "status": "login_required",
                        "message": "需要登录小红书，请先完成登录",
                        "recoverable": True
                    }
                }
                return

            # ==================== 3. 上传图片 ====================
            yield {
                "event": "progress",
                "data": {
                    "step": 3,
                    "total_steps": 7,
                    "status": "uploading_images",
                    "message": f"正在上传 {len(images)} 张图片..."
                }
            }

            # 验证图片文件存在
            valid_images = []
            for img_path in images:
                if os.path.exists(img_path):
                    valid_images.append(img_path)
                else:
                    logger.warning(f"图片文件不存在: {img_path}")

            if not valid_images:
                yield {
                    "event": "error",
                    "data": {
                        "step": 3,
                        "status": "no_valid_images",
                        "message": "没有找到有效的图片文件",
                        "recoverable": False
                    }
                }
                return

            # 使用 AI 代理上传图片
            # 构建图片路径字符串
            image_paths_str = ", ".join(valid_images)

            upload_task = f"""
            在小红书发布页面上传图片。

            图片文件路径: {image_paths_str}

            步骤：
            1. 找到上传图片的区域或按钮（通常是"上传图片"或带有加号的区域）
            2. 点击上传区域
            3. 在文件选择对话框中，依次选择以上图片文件
            4. 等待图片上传完成（看到图片预览）

            如果无法直接选择文件，请尝试使用拖拽或其他上传方式。
            """

            upload_result = self.vibesurf.execute_agent(upload_task, timeout=60)

            if not upload_result.get("success"):
                # 尝试使用直接操作方式上传
                logger.warning("AI 代理上传失败，尝试直接操作...")

                # 使用 JavaScript 触发文件上传
                for img_path in valid_images:
                    js_upload = f"""
                    const input = document.querySelector('input[type="file"]');
                    if (input) {{
                        // 创建一个 DataTransfer 对象来模拟文件选择
                        const dataTransfer = new DataTransfer();
                        // 注意：浏览器安全限制可能阻止此操作
                        console.log('找到文件输入框');
                    }}
                    """
                    self.vibesurf.evaluate_js(js_upload)

            # 等待上传完成
            self.vibesurf.wait(3)

            # ==================== 4. 填写标题 ====================
            yield {
                "event": "progress",
                "data": {
                    "step": 4,
                    "total_steps": 7,
                    "status": "filling_title",
                    "message": "正在填写标题..."
                }
            }

            # 标题限制 20 个字
            safe_title = title[:20] if len(title) > 20 else title

            title_task = f"""
            在小红书发布页面填写标题。

            标题内容: {safe_title}

            步骤：
            1. 找到标题输入框（通常标注为"填写标题"或"标题"）
            2. 点击标题输入框
            3. 输入标题内容
            """

            title_result = self.vibesurf.execute_agent(title_task, timeout=30)

            if not title_result.get("success"):
                logger.warning("AI 代理填写标题失败，尝试直接操作...")
                # 尝试通过获取状态后直接操作
                self.vibesurf.get_browser_state()
                # 尝试查找并点击标题输入框
                self.vibesurf.evaluate_js(f"""
                    const titleInput = document.querySelector('input[placeholder*="标题"], textarea[placeholder*="标题"], [class*="title"] input, [class*="title"] textarea');
                    if (titleInput) {{
                        titleInput.focus();
                        titleInput.value = '{safe_title}';
                        titleInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                """)

            self.vibesurf.wait(1)

            # ==================== 5. 填写正文 ====================
            yield {
                "event": "progress",
                "data": {
                    "step": 5,
                    "total_steps": 7,
                    "status": "filling_content",
                    "message": "正在填写正文..."
                }
            }

            # 转义正文中的特殊字符
            safe_content = content.replace("'", "\\'").replace("\n", "\\n")

            content_task = f"""
            在小红书发布页面填写正文内容。

            正文内容:
            {content}

            步骤：
            1. 找到正文输入框（通常标注为"填写正文"、"添加正文"或较大的文本区域）
            2. 点击正文输入框
            3. 输入正文内容
            """

            content_result = self.vibesurf.execute_agent(content_task, timeout=30)

            if not content_result.get("success"):
                logger.warning("AI 代理填写正文失败，尝试直接操作...")
                self.vibesurf.evaluate_js(f"""
                    const contentInput = document.querySelector('textarea[placeholder*="正文"], [class*="content"] textarea, [class*="editor"] [contenteditable="true"]');
                    if (contentInput) {{
                        contentInput.focus();
                        if (contentInput.tagName === 'TEXTAREA') {{
                            contentInput.value = '{safe_content}';
                            contentInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }} else {{
                            contentInput.innerHTML = '{safe_content}';
                            contentInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                    }}
                """)

            self.vibesurf.wait(1)

            # ==================== 6. 添加标签 ====================
            if tags and len(tags) > 0:
                yield {
                    "event": "progress",
                    "data": {
                        "step": 6,
                        "total_steps": 7,
                        "status": "adding_tags",
                        "message": f"正在添加 {len(tags)} 个标签..."
                    }
                }

                tags_str = ", ".join([f"#{tag}" for tag in tags])

                tags_task = f"""
                在小红书发布页面添加标签/话题。

                标签: {tags_str}

                步骤：
                1. 找到添加标签/话题的区域（通常标注为"添加话题"或"#"图标）
                2. 点击添加标签区域
                3. 依次输入每个标签（在标签前加 # 符号）
                4. 每输入一个标签后按回车确认
                """

                self.vibesurf.execute_agent(tags_task, timeout=30)
                self.vibesurf.wait(1)
            else:
                yield {
                    "event": "progress",
                    "data": {
                        "step": 6,
                        "total_steps": 7,
                        "status": "skipping_tags",
                        "message": "跳过标签添加..."
                    }
                }

            # ==================== 7. 点击发布 ====================
            yield {
                "event": "progress",
                "data": {
                    "step": 7,
                    "total_steps": 7,
                    "status": "publishing",
                    "message": "正在发布..."
                }
            }

            publish_task = """
            在小红书发布页面点击发布按钮。

            步骤：
            1. 找到"发布"或"发布笔记"按钮（通常是页面右上角或底部的醒目按钮）
            2. 点击发布按钮
            3. 如果有确认对话框，点击确认
            4. 等待发布完成
            """

            publish_result = self.vibesurf.execute_agent(publish_task, timeout=30)

            # 等待发布完成
            self.vibesurf.wait(3)

            # 检查发布结果
            state_after = self.vibesurf.get_browser_state()
            raw_response = state_after.get("raw_response", {})
            result_data = raw_response.get("result", {})
            final_url = ""
            if isinstance(result_data, dict):
                final_url = result_data.get("url", "")

            # 判断是否发布成功
            # 通常发布成功后会跳转到作品管理页面或显示成功提示
            if "publish" not in final_url.lower() or "success" in final_url.lower():
                logger.info("发布成功")
                yield {
                    "event": "complete",
                    "data": {
                        "status": "success",
                        "message": "发布成功！",
                        "url": final_url
                    }
                }
            else:
                # 可能还在发布页面，检查是否有错误提示
                yield {
                    "event": "complete",
                    "data": {
                        "status": "unknown",
                        "message": "发布操作已执行，请在浏览器中确认结果",
                        "url": final_url
                    }
                }

        except Exception as e:
            logger.error(f"发布失败: {e}")
            yield {
                "event": "error",
                "data": {
                    "status": "exception",
                    "message": f"发布过程中出错: {str(e)}",
                    "recoverable": False
                }
            }


# 全局服务实例
_publish_service: Optional[PublishService] = None


def get_publish_service() -> PublishService:
    """获取全局发布服务实例"""
    global _publish_service
    if _publish_service is None:
        _publish_service = PublishService()
    return _publish_service


def reset_publish_service():
    """重置全局服务实例"""
    global _publish_service
    _publish_service = None
