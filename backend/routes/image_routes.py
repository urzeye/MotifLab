"""
图片生成相关 API 路由

包含功能：
- 获取图片
- 重新生成单张图片
- 批量重试失败图片
- 获取任务状态
"""

import os
import json
import logging
import re
from flask import Blueprint, request, Response, send_file
from backend.application.services import get_image_generation_application_service
from backend.interfaces.http import json_response
from backend.middleware import is_auth_enabled
from .utils import log_request, log_error

logger = logging.getLogger(__name__)
image_generation_app_service = get_image_generation_application_service()

_SAFE_SEGMENT_RE = re.compile(r'^[A-Za-z0-9._-]+$')
_ALLOWED_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.webp'}


def _validate_path_segment(segment: str, name: str) -> str:
    """校验路径片段，避免路径穿越"""
    if not segment or segment in {'.', '..'}:
        raise ValueError(f"{name} 无效")
    if not _SAFE_SEGMENT_RE.match(segment):
        raise ValueError(f"{name} 包含非法字符")
    for sep in (os.path.sep, os.path.altsep):
        if sep and sep in segment:
            raise ValueError(f"{name} 不能包含路径分隔符")
    return segment


def _safe_join(base_dir: str, *paths: str) -> str:
    """安全拼接路径，确保结果位于基准目录下"""
    base_dir_abs = os.path.abspath(base_dir)
    candidate = os.path.abspath(os.path.join(base_dir_abs, *paths))
    if os.path.commonpath([candidate, base_dir_abs]) != base_dir_abs:
        raise ValueError("路径非法")
    return candidate


def _is_valid_page(page: dict) -> bool:
    """校验页面结构是否满足生成接口要求"""
    if not isinstance(page, dict):
        return False
    if "index" not in page or "type" not in page or "content" not in page:
        return False
    if not isinstance(page.get("index"), int):
        return False
    if not isinstance(page.get("type"), str):
        return False
    if not isinstance(page.get("content"), str):
        return False
    return True


def create_image_blueprint():
    """创建图片路由蓝图（工厂函数，支持多次调用）"""
    image_bp = Blueprint('image', __name__)

    # ==================== 图片获取 ====================

    @image_bp.route('/images/<task_id>/<filename>', methods=['GET'])
    def get_image(task_id, filename):
        """
        获取图片文件

        路径参数：
        - task_id: 任务 ID
        - filename: 文件名

        查询参数：
        - thumbnail: 是否返回缩略图（默认 true）

        返回：
        - 成功：图片文件（本地模式）或重定向到 Supabase Storage（云存储模式）
        - 失败：JSON 错误信息
        """
        from flask import redirect

        try:
            logger.debug(f"获取图片: {task_id}/{filename}")
            safe_task_id = _validate_path_segment(task_id, "task_id")
            safe_filename = _validate_path_segment(filename, "filename")
            ext = os.path.splitext(safe_filename)[1].lower()
            if ext not in _ALLOWED_IMAGE_EXTS:
                return json_response({
                    "success": False,
                    "error": "参数错误：不支持的图片格式"
                }, 400)

            # 检查存储模式
            storage_mode = os.environ.get("HISTORY_STORAGE_MODE", "local")

            # 检查是否请求缩略图
            thumbnail = request.args.get('thumbnail', 'true').lower() == 'true'

            if storage_mode == "supabase":
                # Supabase 模式：重定向到 Storage URL
                from backend.utils.supabase_client import get_image_url

                if thumbnail:
                    thumb_filename = safe_filename if safe_filename.startswith('thumb_') else f"thumb_{safe_filename}"
                    url = get_image_url(safe_task_id, thumb_filename)
                else:
                    url = get_image_url(safe_task_id, safe_filename)

                return redirect(url)

            # 本地模式：从文件系统读取
            history_root = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "history"
            )

            if thumbnail:
                # 尝试返回缩略图
                thumb_filename = safe_filename if safe_filename.startswith('thumb_') else f"thumb_{safe_filename}"
                thumb_filepath = _safe_join(history_root, safe_task_id, thumb_filename)

                # 只有缩略图存在且非空时才返回，避免返回损坏/空文件
                if os.path.exists(thumb_filepath) and os.path.getsize(thumb_filepath) > 0:
                    return send_file(thumb_filepath)

            # 返回原图
            filepath = _safe_join(history_root, safe_task_id, safe_filename)

            if not os.path.exists(filepath):
                return json_response({
                    "success": False,
                    "error": f"图片不存在：{task_id}/{filename}"
                }, 404)

            return send_file(filepath)

        except Exception as e:
            log_error('/images', e)
            error_msg = str(e)
            return json_response({
                "success": False,
                "error": f"获取图片失败: {error_msg}"
            }, 500)

    # ==================== 重试和重新生成 ====================

    @image_bp.route('/retry-failed', methods=['POST'])
    def retry_failed_images():
        """
        批量重试失败的图片（SSE 流式返回）

        请求体：
        - task_id: 任务 ID（必填）
        - pages: 要重试的页面列表（必填）
        - user_prompt: 用户自定义提示词（可选）
        - system_prompt: 用户自定义系统提示词（可选）

        返回：
        SSE 事件流
        """
        try:
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                data = {}
            task_id = data.get('task_id')
            pages = data.get('pages')
            user_prompt = str(data.get('user_prompt') or '').strip()
            system_prompt = str(data.get('system_prompt', '') or '').strip()

            log_request('/retry-failed', {
                'task_id': task_id,
                'pages_count': len(pages) if pages else 0,
                'has_user_prompt': bool(user_prompt),
                'has_system_prompt': bool(system_prompt)
            })

            if not task_id or not isinstance(pages, list) or not pages:
                logger.warning("批量重试请求缺少必要参数")
                return json_response({
                    "success": False,
                    "error": "参数错误：task_id 和 pages 不能为空。\n请提供任务ID和要重试的页面列表。"
                }, 400)
            if any(not _is_valid_page(page) for page in pages):
                return json_response({
                    "success": False,
                    "error": "参数错误：pages 格式不正确。"
                }, 400)

            logger.info(f"🔄 批量重试失败图片: task={task_id}, 共 {len(pages)} 页")

            def generate():
                """SSE 事件生成器"""
                for event in image_generation_app_service.retry_failed_images(
                    task_id,
                    pages,
                    user_prompt=user_prompt,
                    system_prompt=system_prompt,
                ):
                    event_type = event["event"]
                    event_data = event["data"]

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
            log_error('/retry-failed', e)
            error_msg = str(e)
            return json_response({
                "success": False,
                "error": f"批量重试失败。\n错误详情: {error_msg}"
            }, 500)

    @image_bp.route('/regenerate', methods=['POST'])
    def regenerate_image():
        """
        重新生成图片（即使成功的也可以重新生成）

        请求体：
        - task_id: 任务 ID（必填）
        - page: 页面信息（必填）
        - use_reference: 是否使用参考图（默认 true）
        - full_outline: 完整大纲文本（用于上下文）
        - user_topic: 用户原始输入主题
        - user_prompt: 用户自定义提示词（可选）
        - system_prompt: 用户自定义系统提示词（可选）

        返回：
        - success: 是否成功
        - image_url: 新图片 URL
        """
        try:
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                data = {}
            task_id = data.get('task_id')
            page = data.get('page')
            use_reference = data.get('use_reference', True)
            full_outline = data.get('full_outline', '')
            user_topic = data.get('user_topic', '')
            user_prompt = str(data.get('user_prompt') or '').strip()
            system_prompt = str(data.get('system_prompt', '') or '').strip()

            log_request('/regenerate', {
                'task_id': task_id,
                'page_index': page.get('index') if page else None,
                'has_user_prompt': bool(user_prompt),
                'has_system_prompt': bool(system_prompt)
            })

            if not task_id or not _is_valid_page(page):
                logger.warning("重新生成请求缺少必要参数")
                return json_response({
                    "success": False,
                    "error": "参数错误：task_id 和 page 不能为空。\n请提供任务ID和页面信息。"
                }, 400)

            logger.info(f"🔄 重新生成图片: task={task_id}, page={page.get('index')}")
            result = image_generation_app_service.regenerate_image(
                task_id, page, use_reference,
                full_outline=full_outline,
                user_topic=user_topic,
                user_prompt=user_prompt,
                system_prompt=system_prompt,
            )

            if result["success"]:
                logger.info(f"✅ 图片重新生成成功: {result.get('image_url')}")
            else:
                logger.error(f"❌ 图片重新生成失败: {result.get('error')}")

            return json_response(result, 200 if result["success"] else 500)

        except Exception as e:
            log_error('/regenerate', e)
            error_msg = str(e)
            return json_response({
                "success": False,
                "error": f"重新生成图片失败。\n错误详情: {error_msg}"
            }, 500)

    # ==================== 任务状态 ====================

    @image_bp.route('/task/<task_id>', methods=['GET'])
    def get_task_state(task_id):
        """
        获取任务状态

        路径参数：
        - task_id: 任务 ID

        返回：
        - success: 是否成功
        - state: 任务状态
          - generated: 已生成的图片
          - failed: 失败的图片
          - has_cover: 是否有封面图
        """
        try:
            state = image_generation_app_service.get_task_state(task_id)

            if state is None:
                return json_response({
                    "success": False,
                    "error": f"任务不存在：{task_id}\n可能原因：\n1. 任务ID错误\n2. 任务已过期或被清理\n3. 服务重启导致状态丢失"
                }, 404)

            # 不返回封面图片数据（太大）
            safe_state = {
                "generated": state.get("generated", {}),
                "failed": state.get("failed", {}),
                "has_cover": state.get("cover_image") is not None
            }

            return json_response({
                "success": True,
                "state": safe_state
            }, 200)

        except Exception as e:
            error_msg = str(e)
            return json_response({
                "success": False,
                "error": f"获取任务状态失败。\n错误详情: {error_msg}"
            }, 500)

    # ==================== 健康检查 ====================

    @image_bp.route('/health', methods=['GET'])
    def health_check():
        """
        健康检查接口

        返回：
        - success: 服务是否正常
        - message: 状态消息
        """
        return json_response({
            "success": True,
            "message": "服务正常运行",
            "auth_required": is_auth_enabled(),
            "rate_limit": os.environ.get('MOTIFLAB_RATE_LIMIT', '60 per minute')
        }, 200)

    return image_bp
