"""
发布相关 API 路由

包含功能：
- VibeSurf 状态检查
- 小红书登录状态检查
- 打开登录页面
- 发布图文到小红书（SSE 流式返回）
"""

import json
import logging
from flask import Blueprint, request, jsonify, Response
from backend.services.publish import get_publish_service
from .utils import log_request, log_error

logger = logging.getLogger(__name__)


def create_publish_blueprint():
    """创建发布路由蓝图（工厂函数，支持多次调用）"""
    publish_bp = Blueprint('publish', __name__, url_prefix='/publish')

    # ==================== VibeSurf 状态 ====================

    @publish_bp.route('/status', methods=['GET'])
    def check_vibesurf_status():
        """
        检查 VibeSurf 状态

        返回：
        - running: bool, VibeSurf 是否运行中
        - message: str, 状态消息
        - version: str, 版本信息
        """
        try:
            log_request('/publish/status', {})
            logger.debug("检查 VibeSurf 状态")

            publish_service = get_publish_service()
            result = publish_service.check_vibesurf_status()

            return jsonify({
                "success": True,
                **result
            }), 200

        except Exception as e:
            log_error('/publish/status', e)
            return jsonify({
                "success": False,
                "running": False,
                "message": f"检查 VibeSurf 状态失败: {str(e)}"
            }), 500

    # ==================== 登录状态 ====================

    @publish_bp.route('/login-check', methods=['GET'])
    def check_login_status():
        """
        检查小红书登录状态

        返回：
        - logged_in: bool, 是否已登录
        - message: str, 状态消息
        - vibesurf_running: bool, VibeSurf 是否运行
        """
        try:
            log_request('/publish/login-check', {})
            logger.info("检查小红书登录状态")

            publish_service = get_publish_service()
            result = publish_service.check_login_status()

            return jsonify({
                "success": True,
                **result
            }), 200

        except Exception as e:
            log_error('/publish/login-check', e)
            return jsonify({
                "success": False,
                "logged_in": False,
                "message": f"检查登录状态失败: {str(e)}"
            }), 500

    @publish_bp.route('/login', methods=['POST'])
    def open_login_page():
        """
        打开小红书登录页面

        返回：
        - success: bool
        - message: str
        """
        try:
            log_request('/publish/login', {})
            logger.info("打开小红书登录页面")

            publish_service = get_publish_service()
            result = publish_service.open_login_page()

            status_code = 200 if result["success"] else 500
            return jsonify(result), status_code

        except Exception as e:
            log_error('/publish/login', e)
            return jsonify({
                "success": False,
                "message": f"打开登录页面失败: {str(e)}"
            }), 500

    # ==================== 发布到小红书 ====================

    @publish_bp.route('/xiaohongshu', methods=['POST'])
    def publish_to_xiaohongshu():
        """
        发布图文到小红书（SSE 流式返回）

        请求体：
        - images: list, 图片路径列表（必填）
        - title: str, 标题（必填，最多 20 字）
        - content: str, 正文内容（必填）
        - tags: list, 标签列表（可选）

        返回：
        SSE 事件流，包含以下事件类型：
        - progress: 发布进度
        - error: 发布错误
        - complete: 发布完成
        """
        try:
            data = request.get_json()
            images = data.get('images', [])
            title = data.get('title', '')
            content = data.get('content', '')
            tags = data.get('tags', [])

            log_request('/publish/xiaohongshu', {
                'images_count': len(images),
                'title': title[:20] if title else None,
                'content_length': len(content) if content else 0,
                'tags_count': len(tags) if tags else 0
            })

            # 参数验证
            if not images:
                logger.warning("发布请求缺少图片")
                return jsonify({
                    "success": False,
                    "error": "参数错误：images 不能为空。\n请提供要发布的图片路径列表。"
                }), 400

            if not title:
                logger.warning("发布请求缺少标题")
                return jsonify({
                    "success": False,
                    "error": "参数错误：title 不能为空。\n请提供发布标题。"
                }), 400

            if not content:
                logger.warning("发布请求缺少正文")
                return jsonify({
                    "success": False,
                    "error": "参数错误：content 不能为空。\n请提供发布正文内容。"
                }), 400

            logger.info(f"开始发布到小红书: title={title[:20]}..., images={len(images)}")
            publish_service = get_publish_service()

            def generate():
                """SSE 事件生成器"""
                for event in publish_service.publish_to_xiaohongshu(
                    images=images,
                    title=title,
                    content=content,
                    tags=tags
                ):
                    event_type = event["event"]
                    event_data = event["data"]

                    # 格式化为 SSE 格式
                    yield f"event: {event_type}\n"
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

            return Response(
                generate(),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no',
                }
            )

        except Exception as e:
            log_error('/publish/xiaohongshu', e)
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"发布失败。\n错误详情: {error_msg}\n建议：检查 VibeSurf 服务状态和网络连接"
            }), 500

    # ==================== 健康检查 ====================

    @publish_bp.route('/health', methods=['GET'])
    def health_check():
        """
        健康检查接口

        返回：
        - success: 服务是否正常
        - message: 状态消息
        - vibesurf: VibeSurf 状态
        """
        try:
            publish_service = get_publish_service()
            vibesurf_status = publish_service.check_vibesurf_status()

            return jsonify({
                "success": True,
                "message": "发布服务正常运行",
                "vibesurf": vibesurf_status
            }), 200

        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"服务异常: {str(e)}"
            }), 500

    return publish_bp
