"""
图片生成相关 API 路由

包含功能：
- 批量生成图片（SSE 流式返回）
- 获取图片
- 重试/重新生成单张图片
- 批量重试失败图片
- 获取任务状态
"""

import os
import json
import base64
import logging
import re
from flask import Blueprint, request, Response, send_file
from backend.interfaces.http import json_response
from backend.services.image import get_image_service
from backend.middleware import is_auth_enabled
from .utils import log_request, log_error

logger = logging.getLogger(__name__)

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

    # ==================== 图片生成 ====================

    @image_bp.route('/generate', methods=['POST'])
    def generate_images():
        """
        批量生成图片（SSE 流式返回）

        请求体：
        - pages: 页面列表（必填）
        - task_id: 任务 ID
        - full_outline: 完整大纲文本
        - user_topic: 用户原始输入主题
        - user_images: base64 编码的用户参考图片列表
        - custom_prompt: 用户自定义提示词（可选）

        返回：
        SSE 事件流，包含以下事件类型：
        - image: 单张图片生成完成
        - error: 生成错误
        - complete: 全部完成
        """
        try:
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                data = {}
            pages = data.get('pages')
            task_id = data.get('task_id')
            full_outline = data.get('full_outline', '')
            user_topic = data.get('user_topic', '')
            custom_prompt = str(data.get('custom_prompt', '') or '').strip()

            # 解析 base64 格式的用户参考图片
            user_images = _parse_base64_images(data.get('user_images', []))

            log_request('/generate', {
                'pages_count': len(pages) if pages else 0,
                'task_id': task_id,
                'user_topic': user_topic[:50] if user_topic else None,
                'user_images': user_images,
                'has_custom_prompt': bool(custom_prompt)
            })

            if not isinstance(pages, list) or not pages:
                logger.warning("图片生成请求缺少 pages 参数")
                return json_response({
                    "success": False,
                    "error": "参数错误：pages 不能为空。\n请提供要生成的页面列表数据。"
                }, 400)
            if any(not _is_valid_page(page) for page in pages):
                return json_response({
                    "success": False,
                    "error": "参数错误：pages 格式不正确。"
                }, 400)

            logger.info(f"🖼️  开始图片生成任务: {task_id}, 共 {len(pages)} 页")
            image_service = get_image_service()

            def generate():
                """SSE 事件生成器"""
                completed_indices = set()
                failed_indices = set()
                sent_finish = False

                try:
                    for event in image_service.generate_images(
                        pages, task_id, full_outline,
                        user_images=user_images if user_images else None,
                        user_topic=user_topic,
                        custom_prompt=custom_prompt
                    ):
                        event_type = event["event"]
                        event_data = event["data"]

                        if event_type == "complete":
                            index = event_data.get("index")
                            if isinstance(index, int) and index >= 0:
                                completed_indices.add(index)
                        elif event_type == "error":
                            index = event_data.get("index")
                            if isinstance(index, int) and index >= 0:
                                failed_indices.add(index)
                        elif event_type == "finish":
                            sent_finish = True

                        # 格式化为 SSE 格式
                        yield f"event: {event_type}\n"
                        yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                except Exception as e:
                    logger.error(f"图片 SSE 流异常中断: {e}", exc_info=True)

                    error_data = {
                        "index": -1,
                        "status": "error",
                        "message": f"服务器内部错误: {str(e)}",
                        "retryable": True,
                        "phase": "system"
                    }
                    yield "event: error\n"
                    yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

                    if not sent_finish:
                        total = len(pages) if pages else 0
                        completed = len(completed_indices)
                        failed = max(len(failed_indices), total - completed)
                        finish_data = {
                            "success": False,
                            "task_id": task_id,
                            "images": [],
                            "total": total,
                            "completed": completed,
                            "failed": failed,
                            "failed_indices": sorted(failed_indices)
                        }
                        yield "event: finish\n"
                        yield f"data: {json.dumps(finish_data, ensure_ascii=False)}\n\n"

            return Response(
                generate(),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no',
                }
            )

        except Exception as e:
            log_error('/generate', e)
            error_msg = str(e)
            return json_response({
                "success": False,
                "error": f"图片生成异常。\n错误详情: {error_msg}\n建议：检查图片生成服务配置和后端日志"
            }, 500)

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

    @image_bp.route('/retry', methods=['POST'])
    def retry_single_image():
        """
        重试生成单张失败的图片

        请求体：
        - task_id: 任务 ID（必填）
        - page: 页面信息（必填）
        - use_reference: 是否使用参考图（默认 true）
        - custom_prompt: 用户自定义提示词（可选）

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
            custom_prompt = str(data.get('custom_prompt', '') or '').strip()

            log_request('/retry', {
                'task_id': task_id,
                'page_index': page.get('index') if page else None
            })

            if not task_id or not _is_valid_page(page):
                logger.warning("重试请求缺少必要参数")
                return json_response({
                    "success": False,
                    "error": "参数错误：task_id 和 page 不能为空。\n请提供任务ID和页面信息。"
                }, 400)

            logger.info(f"🔄 重试生成图片: task={task_id}, page={page.get('index')}")
            image_service = get_image_service()
            result = image_service.retry_single_image(
                task_id,
                page,
                use_reference,
                custom_prompt=custom_prompt,
            )

            if result["success"]:
                logger.info(f"✅ 图片重试成功: {result.get('image_url')}")
            else:
                logger.error(f"❌ 图片重试失败: {result.get('error')}")

            return json_response(result, 200 if result["success"] else 500)

        except Exception as e:
            log_error('/retry', e)
            error_msg = str(e)
            return json_response({
                "success": False,
                "error": f"重试图片生成失败。\n错误详情: {error_msg}"
            }, 500)

    @image_bp.route('/retry-failed', methods=['POST'])
    def retry_failed_images():
        """
        批量重试失败的图片（SSE 流式返回）

        请求体：
        - task_id: 任务 ID（必填）
        - pages: 要重试的页面列表（必填）

        返回：
        SSE 事件流
        """
        try:
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                data = {}
            task_id = data.get('task_id')
            pages = data.get('pages')

            log_request('/retry-failed', {
                'task_id': task_id,
                'pages_count': len(pages) if pages else 0
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
            image_service = get_image_service()

            def generate():
                """SSE 事件生成器"""
                for event in image_service.retry_failed_images(task_id, pages):
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
        - custom_prompt: 用户自定义提示词（可选）

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
            custom_prompt = str(data.get('custom_prompt', '') or '').strip()

            log_request('/regenerate', {
                'task_id': task_id,
                'page_index': page.get('index') if page else None
            })

            if not task_id or not _is_valid_page(page):
                logger.warning("重新生成请求缺少必要参数")
                return json_response({
                    "success": False,
                    "error": "参数错误：task_id 和 page 不能为空。\n请提供任务ID和页面信息。"
                }, 400)

            logger.info(f"🔄 重新生成图片: task={task_id}, page={page.get('index')}")
            image_service = get_image_service()
            result = image_service.regenerate_image(
                task_id, page, use_reference,
                full_outline=full_outline,
                user_topic=user_topic,
                custom_prompt=custom_prompt,
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
            image_service = get_image_service()
            state = image_service.get_task_state(task_id)

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
            "rate_limit": os.environ.get('REDINK_RATE_LIMIT', '60 per minute')
        }, 200)

    return image_bp


# ==================== 辅助函数 ====================

def _parse_base64_images(images_base64: list) -> list:
    """
    解析 base64 编码的图片列表

    Args:
        images_base64: base64 编码的图片字符串列表

    Returns:
        list: 解码后的图片二进制数据列表
    """
    if not images_base64 or not isinstance(images_base64, list):
        return []

    images = []
    for img_b64 in images_base64:
        if not isinstance(img_b64, str):
            continue
        # 移除可能的 data URL 前缀（如 data:image/png;base64,）
        if ',' in img_b64:
            img_b64 = img_b64.split(',', 1)[1]
        try:
            images.append(base64.b64decode(img_b64))
        except Exception:
            logger.warning("忽略无效的 base64 图片输入")
            continue

    return images
