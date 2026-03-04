"""
大纲生成相关 API 路由

包含功能：
- 生成大纲（支持图片上传）
"""

import time
import base64
import json
import logging
from flask import Blueprint, request, Response, stream_with_context
from backend.application.services import get_outline_application_service
from backend.interfaces.http import json_response
from .utils import log_request, log_error

logger = logging.getLogger(__name__)
outline_application_service = get_outline_application_service()


def create_outline_blueprint():
    """创建大纲路由蓝图（工厂函数，支持多次调用）"""
    outline_bp = Blueprint('outline', __name__)

    @outline_bp.route('/outline', methods=['POST'])
    def generate_outline():
        """
        生成大纲（支持图片上传）

        请求格式：
        1. multipart/form-data（带图片文件）
           - topic: 主题文本
           - images: 图片文件列表
           - source_content: 网页正文（可选）

        2. application/json（无图片或 base64 图片）
           - topic: 主题文本
           - images: base64 编码的图片数组（可选）
           - source_content: 网页正文（可选）

        返回：
        - success: 是否成功
        - outline: 原始大纲文本
        - pages: 解析后的页面列表
        """
        start_time = time.time()

        try:
            # 解析请求数据
            (
                topic,
                images,
                source_content,
                template_ref,
                enable_search,
                search_provider,
            ) = _parse_outline_request()

            log_request('/outline', {
                'topic': topic,
                'images': images,
                'has_source_content': bool(source_content),
                'has_template_ref': bool(template_ref),
                'enable_search': enable_search,
                'search_provider': search_provider
            })

            # 验证必填参数
            if not topic:
                logger.warning("大纲生成请求缺少 topic 参数")
                return json_response({
                    "success": False,
                    "error": "参数错误：topic 不能为空。\n请提供要生成图文的主题内容。"
                }, 400)

            # 调用大纲生成服务
            logger.info(f"🔄 开始生成大纲，主题: {topic[:50]}...")
            result = outline_application_service.generate_outline(
                topic,
                images if images else None,
                source_content=source_content,
                template_ref=template_ref,
                enable_search=enable_search,
                search_provider=search_provider,
            )

            # 记录结果
            elapsed = time.time() - start_time
            if result["success"]:
                logger.info(f"✅ 大纲生成成功，耗时 {elapsed:.2f}s，共 {len(result.get('pages', []))} 页")
                return json_response(result, 200)
            else:
                logger.error(f"❌ 大纲生成失败: {result.get('error', '未知错误')}")
                return json_response(result, 500)

        except Exception as e:
            log_error('/outline', e)
            error_msg = str(e)
            return json_response({
                "success": False,
                "error": f"大纲生成异常。\n错误详情: {error_msg}\n建议：检查后端日志获取更多信息"
            }, 500)

    @outline_bp.route('/outline/stream', methods=['POST'])
    def generate_outline_stream():
        """
        流式生成大纲（SSE）

        请求参数与 /outline 保持一致，额外支持：
        - enable_search: bool，是否开启联网搜索增强（主题检索 + 可选模型联网能力，默认 false）
        - search_provider: str，可选，指定本次联网增强使用的搜索服务商
        """
        start_time = time.time()
        try:
            (
                topic,
                images,
                source_content,
                template_ref,
                enable_search,
                search_provider,
            ) = _parse_outline_request()

            log_request('/outline/stream', {
                'topic': topic,
                'images': images,
                'has_source_content': bool(source_content),
                'has_template_ref': bool(template_ref),
                'enable_search': enable_search,
                'search_provider': search_provider
            })

            if not topic:
                return json_response({
                    "success": False,
                    "error": "参数错误：topic 不能为空。\n请提供要生成图文的主题内容。"
                }, 400)

            def generate_events():
                try:
                    start_event = {
                        "success": True,
                        "message": "开始生成大纲"
                    }
                    yield f"event: start\ndata: {json.dumps(start_event, ensure_ascii=False)}\n\n"

                    result = outline_application_service.generate_outline(
                        topic,
                        images if images else None,
                        source_content=source_content,
                        template_ref=template_ref,
                        enable_search=enable_search,
                        search_provider=search_provider,
                    )

                    elapsed = time.time() - start_time
                    if not result.get("success"):
                        logger.error(f"❌ 流式大纲生成失败: {result.get('error', '未知错误')}")
                        error_event = {
                            "success": False,
                            "error": result.get("error", "大纲生成失败")
                        }
                        yield f"event: error\ndata: {json.dumps(error_event, ensure_ascii=False)}\n\n"
                        return

                    logger.info(
                        f"✅ 流式大纲生成成功，耗时 {elapsed:.2f}s，共 {len(result.get('pages', []))} 页"
                    )
                    finish_event = {
                        "success": True,
                        "outline": result.get("outline", ""),
                        "pages": result.get("pages", []),
                        "has_images": result.get("has_images", False),
                        "elapsed": round(elapsed, 2)
                    }
                    yield f"event: finish\ndata: {json.dumps(finish_event, ensure_ascii=False)}\n\n"

                except Exception as e:
                    logger.error(f"/outline/stream 流式处理异常: {e}", exc_info=True)
                    error_event = {
                        "success": False,
                        "error": str(e)
                    }
                    yield f"event: error\ndata: {json.dumps(error_event, ensure_ascii=False)}\n\n"

            return Response(
                stream_with_context(generate_events()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no',
                }
            )

        except Exception as e:
            log_error('/outline/stream', e)
            return json_response({
                "success": False,
                "error": f"初始化流式大纲生成失败: {str(e)}"
            }, 500)

    @outline_bp.route('/outline/edit/stream', methods=['POST'])
    def edit_outline_stream():
        """
        编辑大纲并流式返回每页文案与配图建议（SSE）

        请求体：
        - topic: 主题（必填）
        - current_outline: 当前大纲文本（可选）
        - current_pages: 当前页面列表（可选）
        - revision_request: 修改需求（revise 模式必填）
        - mode: suggest_only | revise（默认 revise）
        - template_ref: 模板参考（可选）
        """
        try:
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                data = {}

            topic = str(data.get('topic', '')).strip()
            current_outline = str(data.get('current_outline', '') or '')
            current_pages = data.get('current_pages', [])
            revision_request = str(data.get('revision_request', '') or '')
            mode = str(data.get('mode', 'revise') or 'revise').strip().lower()
            template_ref = data.get('template_ref')
            if not isinstance(template_ref, dict):
                template_ref = None

            if not topic:
                return json_response({
                    "success": False,
                    "error": "参数错误：topic 不能为空"
                }, 400)

            if mode not in {'suggest_only', 'revise'}:
                return json_response({
                    "success": False,
                    "error": "参数错误：mode 仅支持 suggest_only / revise"
                }, 400)

            if mode == 'revise' and not revision_request.strip():
                return json_response({
                    "success": False,
                    "error": "参数错误：revise 模式下 revision_request 不能为空"
                }, 400)

            if not isinstance(current_pages, list):
                current_pages = []
            else:
                current_pages = [p for p in current_pages if _is_valid_page(p)]

            log_request('/outline/edit/stream', {
                'topic': topic[:80],
                'mode': mode,
                'current_pages': current_pages,
                'has_current_outline': bool(current_outline.strip()),
                'revision_request': revision_request[:120],
                'has_template_ref': bool(template_ref)
            })

            def generate_events():
                try:
                    start_event = {
                        "success": True,
                        "mode": mode,
                        "message": "开始处理大纲编辑请求"
                    }
                    yield f"event: start\ndata: {json.dumps(start_event, ensure_ascii=False)}\n\n"

                    result = outline_application_service.edit_outline_with_suggestions(
                        topic=topic,
                        current_outline=current_outline,
                        current_pages=current_pages,
                        revision_request=revision_request,
                        mode=mode,
                        template_ref=template_ref
                    )

                    if not result.get("success"):
                        error_event = {
                            "success": False,
                            "mode": mode,
                            "error": result.get("error", "编辑失败")
                        }
                        yield f"event: error\ndata: {json.dumps(error_event, ensure_ascii=False)}\n\n"
                        return

                    pages = result.get("pages", []) or []
                    for page in pages:
                        page_event = {
                            "success": True,
                            "mode": mode,
                            "page": page
                        }
                        yield f"event: page\ndata: {json.dumps(page_event, ensure_ascii=False)}\n\n"

                    finish_event = {
                        "success": True,
                        "mode": mode,
                        "outline": result.get("outline", ""),
                        "pages": pages
                    }
                    yield f"event: finish\ndata: {json.dumps(finish_event, ensure_ascii=False)}\n\n"

                except Exception as e:
                    logger.error(f"/outline/edit/stream 流式处理异常: {e}", exc_info=True)
                    error_event = {
                        "success": False,
                        "mode": mode,
                        "error": str(e)
                    }
                    yield f"event: error\ndata: {json.dumps(error_event, ensure_ascii=False)}\n\n"

            return Response(
                stream_with_context(generate_events()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no',
                }
            )

        except Exception as e:
            log_error('/outline/edit/stream', e)
            return json_response({
                "success": False,
                "error": f"初始化流式编辑失败: {str(e)}"
            }, 500)

    return outline_bp


def _parse_outline_request():
    """
    解析大纲生成请求

    支持两种格式：
    1. multipart/form-data - 用于文件上传
    2. application/json - 用于 base64 图片

    返回：
        tuple: (topic, images, source_content, template_ref, enable_search, search_provider)
        - topic: 主题
        - images: 图片二进制数组
        - source_content: 网页抓取正文
        - template_ref: 模板参考
        - enable_search: 是否启用联网搜索增强
        - search_provider: 本次请求指定的搜索服务商（可选）
    """
    # 检查是否是 multipart/form-data（带图片文件）
    if request.content_type and 'multipart/form-data' in request.content_type:
        topic = request.form.get('topic')
        source_content = request.form.get('source_content')
        enable_search = _parse_bool(request.form.get('enable_search'), False)
        search_provider = (request.form.get('search_provider') or '').strip() or None
        template_ref_raw = request.form.get('template_ref')
        template_ref = None
        images = []

        if template_ref_raw:
            try:
                parsed = json.loads(template_ref_raw)
                template_ref = parsed if isinstance(parsed, dict) else None
            except Exception:
                logger.warning("忽略无效的 template_ref（multipart）")

        # 获取上传的图片文件
        if 'images' in request.files:
            files = request.files.getlist('images')
            for file in files:
                if file and file.filename:
                    image_data = file.read()
                    images.append(image_data)

        return topic, images, source_content, template_ref, enable_search, search_provider

    # JSON 请求（无图片或 base64 图片）
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        data = {}
    topic = data.get('topic')
    source_content = data.get('source_content')
    enable_search = _parse_bool(data.get('enable_search'), False)
    search_provider = str(data.get('search_provider') or '').strip() or None
    template_ref = data.get('template_ref')
    if not isinstance(template_ref, dict):
        template_ref = None
    images = []

    # 支持 base64 格式的图片
    images_base64 = data.get('images', [])
    if not isinstance(images_base64, list):
        images_base64 = []
    if images_base64:
        for img_b64 in images_base64:
            if not isinstance(img_b64, str):
                continue
            # 移除可能的 data URL 前缀
            if ',' in img_b64:
                img_b64 = img_b64.split(',', 1)[1]
            try:
                images.append(base64.b64decode(img_b64))
            except Exception:
                logger.warning("忽略无效的 base64 图片输入")
                continue

    return topic, images, source_content, template_ref, enable_search, search_provider


def _parse_bool(value, default: bool = False) -> bool:
    """解析布尔值，兼容字符串/数字输入。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {'1', 'true', 'yes', 'on'}:
            return True
        if normalized in {'0', 'false', 'no', 'off', ''}:
            return False
    return default


def _is_valid_page(page: dict) -> bool:
    """校验页面结构"""
    if not isinstance(page, dict):
        return False
    if "content" not in page:
        return False
    if not isinstance(page.get("content"), str):
        return False
    if "type" in page and not isinstance(page.get("type"), str):
        return False
    return True
