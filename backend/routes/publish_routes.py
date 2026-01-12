"""
发布相关 API 路由

提供小红书发布功能的 REST API 接口。
"""

import logging
import asyncio
from flask import Blueprint, request, jsonify

from backend.services.publish import publish_service

logger = logging.getLogger(__name__)


def create_publish_blueprint():
    """创建发布路由蓝图"""
    publish_bp = Blueprint('publish', __name__)

    # ==================== MCP 状态 ====================

    @publish_bp.route('/publish/status', methods=['GET'])
    def get_mcp_status():
        """
        获取 MCP 服务状态

        返回：
        - running: MCP 服务是否运行
        - binary_installed: 二进制文件是否已安装
        - url: MCP 服务地址
        """
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            status = loop.run_until_complete(publish_service.get_mcp_status())
            loop.close()

            return jsonify({
                "success": True,
                **status
            })
        except Exception as e:
            logger.error(f"获取 MCP 状态失败: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    # ==================== 登录状态 ====================

    @publish_bp.route('/publish/login-check', methods=['GET'])
    def check_login():
        """
        检查小红书登录状态

        返回：
        - logged_in: 是否已登录
        - message: 状态消息
        - user_info: 用户信息（如果已登录）
        """
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(publish_service.check_login())
            loop.close()

            return jsonify(result)
        except Exception as e:
            logger.error(f"检查登录状态失败: {e}")
            return jsonify({
                "success": False,
                "logged_in": False,
                "message": f"检查失败: {str(e)}"
            }), 500

    @publish_bp.route('/publish/login', methods=['POST'])
    def open_login():
        """
        打开小红书登录页面

        用户需要在弹出的浏览器中手动完成登录。
        """
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(publish_service.open_login_page())
            loop.close()

            return jsonify(result)
        except Exception as e:
            logger.error(f"打开登录页面失败: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    # ==================== 发布功能 ====================

    @publish_bp.route('/publish/xiaohongshu', methods=['POST'])
    def publish_to_xiaohongshu():
        """
        发布内容到小红书

        请求体：
        - title: 标题（必填，最多20字）
        - content: 正文（必填）
        - images: 图片路径列表（必填）
        - tags: 标签列表（可选）

        返回：
        - success: 是否成功
        - message: 结果消息
        - post_url: 发布成功后的链接
        """
        try:
            data = request.get_json()

            title = data.get('title')
            content = data.get('content')
            images = data.get('images', [])
            tags = data.get('tags', [])

            # 参数校验
            if not title:
                return jsonify({
                    "success": False,
                    "error": "标题不能为空"
                }), 400

            if not content:
                return jsonify({
                    "success": False,
                    "error": "正文不能为空"
                }), 400

            if not images or len(images) == 0:
                return jsonify({
                    "success": False,
                    "error": "至少需要一张图片"
                }), 400

            # 执行发布
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                publish_service.publish(
                    title=title,
                    content=content,
                    images=images,
                    tags=tags
                )
            )
            loop.close()

            status_code = 200 if result.get('success') else 500
            return jsonify(result), status_code

        except Exception as e:
            logger.error(f"发布失败: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @publish_bp.route('/publish/video', methods=['POST'])
    def publish_video():
        """
        发布视频到小红书

        请求体：
        - title: 标题
        - content: 正文
        - video_path: 视频文件路径
        - cover_image: 封面图片路径（可选）
        - tags: 标签列表（可选）
        """
        try:
            data = request.get_json()

            title = data.get('title')
            content = data.get('content')
            video_path = data.get('video_path')
            cover_image = data.get('cover_image')
            tags = data.get('tags', [])

            if not title or not content or not video_path:
                return jsonify({
                    "success": False,
                    "error": "标题、正文和视频路径为必填项"
                }), 400

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                publish_service.publish_with_video(
                    title=title,
                    content=content,
                    video_path=video_path,
                    cover_image=cover_image,
                    tags=tags
                )
            )
            loop.close()

            status_code = 200 if result.get('success') else 500
            return jsonify(result), status_code

        except Exception as e:
            logger.error(f"发布视频失败: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    # ==================== 帖子管理 ====================

    @publish_bp.route('/publish/posts', methods=['GET'])
    def list_posts():
        """
        获取我的帖子列表

        查询参数：
        - page: 页码（默认1）
        - limit: 每页数量（默认20）
        """
        try:
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 20, type=int)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                publish_service.list_my_posts(page=page, limit=limit)
            )
            loop.close()

            return jsonify(result)
        except Exception as e:
            logger.error(f"获取帖子列表失败: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @publish_bp.route('/publish/search', methods=['GET'])
    def search_posts():
        """
        搜索帖子

        查询参数：
        - keyword: 搜索关键词
        - page: 页码（默认1）
        """
        try:
            keyword = request.args.get('keyword', '')
            page = request.args.get('page', 1, type=int)

            if not keyword:
                return jsonify({
                    "success": False,
                    "error": "搜索关键词不能为空"
                }), 400

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                publish_service.search_posts(keyword=keyword, page=page)
            )
            loop.close()

            return jsonify(result)
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    return publish_bp
