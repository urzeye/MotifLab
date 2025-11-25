"""API 路由"""
import json
from flask import Blueprint, request, jsonify, Response, send_file
from backend.services.outline import get_outline_service
from backend.services.image import get_image_service
from backend.services.history import get_history_service

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/outline', methods=['POST'])
def generate_outline():
    """生成大纲（支持图片上传）"""
    try:
        # 检查是否是 multipart/form-data（带图片）
        if request.content_type and 'multipart/form-data' in request.content_type:
            topic = request.form.get('topic')
            # 获取上传的图片
            images = []
            if 'images' in request.files:
                files = request.files.getlist('images')
                for file in files:
                    if file and file.filename:
                        image_data = file.read()
                        images.append(image_data)
        else:
            # JSON 请求（无图片或 base64 图片）
            data = request.get_json()
            topic = data.get('topic')
            # 支持 base64 格式的图片
            images_base64 = data.get('images', [])
            images = []
            if images_base64:
                import base64
                for img_b64 in images_base64:
                    # 移除可能的 data URL 前缀
                    if ',' in img_b64:
                        img_b64 = img_b64.split(',')[1]
                    images.append(base64.b64decode(img_b64))

        if not topic:
            return jsonify({
                "success": False,
                "error": "参数错误：topic 不能为空。\n请提供要生成图文的主题内容。"
            }), 400

        # 调用大纲生成服务
        outline_service = get_outline_service()
        result = outline_service.generate_outline(topic, images if images else None)

        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 500

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"大纲生成异常。\n错误详情: {error_msg}\n建议：检查后端日志获取更多信息"
        }), 500


@api_bp.route('/generate', methods=['POST'])
def generate_images():
    """生成图片（SSE 流式返回，支持用户上传参考图片）"""
    try:
        # JSON 请求
        data = request.get_json()
        pages = data.get('pages')
        task_id = data.get('task_id')
        full_outline = data.get('full_outline', '')
        user_topic = data.get('user_topic', '')  # 用户原始输入
        # 支持 base64 格式的用户参考图片
        user_images_base64 = data.get('user_images', [])
        user_images = []
        if user_images_base64:
            import base64
            for img_b64 in user_images_base64:
                if ',' in img_b64:
                    img_b64 = img_b64.split(',')[1]
                user_images.append(base64.b64decode(img_b64))

        if not pages:
            return jsonify({
                "success": False,
                "error": "参数错误：pages 不能为空。\n请提供要生成的页面列表数据。"
            }), 400

        # 获取图片生成服务
        image_service = get_image_service()

        def generate():
            """SSE 生成器"""
            for event in image_service.generate_images(
                pages, task_id, full_outline,
                user_images=user_images if user_images else None,
                user_topic=user_topic
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
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"图片生成异常。\n错误详情: {error_msg}\n建议：检查图片生成服务配置和后端日志"
        }), 500


@api_bp.route('/images/<filename>', methods=['GET'])
def get_image(filename):
    """获取图片"""
    try:
        image_service = get_image_service()
        filepath = image_service.get_image_path(filename)

        return send_file(filepath, mimetype='image/png')

    except FileNotFoundError:
        return jsonify({
            "success": False,
            "error": f"图片不存在：{filename}\n可能原因：\n1. 图片已被删除\n2. 文件路径错误\n3. 图片生成失败"
        }), 404
    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"获取图片失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/retry', methods=['POST'])
def retry_single_image():
    """重试生成单张图片"""
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        page = data.get('page')
        use_reference = data.get('use_reference', True)

        if not task_id or not page:
            return jsonify({
                "success": False,
                "error": "参数错误：task_id 和 page 不能为空。\n请提供任务ID和页面信息。"
            }), 400

        image_service = get_image_service()
        result = image_service.retry_single_image(task_id, page, use_reference)

        return jsonify(result), 200 if result["success"] else 500

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"重试图片生成失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/retry-failed', methods=['POST'])
def retry_failed_images():
    """批量重试失败的图片（SSE 流式返回）"""
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        pages = data.get('pages')

        if not task_id or not pages:
            return jsonify({
                "success": False,
                "error": "参数错误：task_id 和 pages 不能为空。\n请提供任务ID和要重试的页面列表。"
            }), 400

        image_service = get_image_service()

        def generate():
            """SSE 生成器"""
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
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"批量重试失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/regenerate', methods=['POST'])
def regenerate_image():
    """重新生成图片（即使成功的也可以重新生成）"""
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        page = data.get('page')
        use_reference = data.get('use_reference', True)

        if not task_id or not page:
            return jsonify({
                "success": False,
                "error": "参数错误：task_id 和 page 不能为空。\n请提供任务ID和页面信息。"
            }), 400

        image_service = get_image_service()
        result = image_service.regenerate_image(task_id, page, use_reference)

        return jsonify(result), 200 if result["success"] else 500

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"重新生成图片失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/task/<task_id>', methods=['GET'])
def get_task_state(task_id):
    """获取任务状态"""
    try:
        image_service = get_image_service()
        state = image_service.get_task_state(task_id)

        if state is None:
            return jsonify({
                "success": False,
                "error": f"任务不存在：{task_id}\n可能原因：\n1. 任务ID错误\n2. 任务已过期或被清理\n3. 服务重启导致状态丢失"
            }), 404

        # 不返回封面图片数据（太大）
        safe_state = {
            "generated": state.get("generated", {}),
            "failed": state.get("failed", {}),
            "has_cover": state.get("cover_image") is not None
        }

        return jsonify({
            "success": True,
            "state": safe_state
        }), 200

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"获取任务状态失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        "success": True,
        "message": "服务正常运行"
    }), 200


# ==================== 历史记录相关 API ====================

@api_bp.route('/history', methods=['POST'])
def create_history():
    """创建历史记录"""
    try:
        data = request.get_json()
        topic = data.get('topic')
        outline = data.get('outline')
        task_id = data.get('task_id')

        if not topic or not outline:
            return jsonify({
                "success": False,
                "error": "参数错误：topic 和 outline 不能为空。\n请提供主题和大纲内容。"
            }), 400

        history_service = get_history_service()
        record_id = history_service.create_record(topic, outline, task_id)

        return jsonify({
            "success": True,
            "record_id": record_id
        }), 200

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"创建历史记录失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/history', methods=['GET'])
def list_history():
    """获取历史记录列表"""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        status = request.args.get('status')

        history_service = get_history_service()
        result = history_service.list_records(page, page_size, status)

        return jsonify({
            "success": True,
            **result
        }), 200

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"获取历史记录列表失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/history/<record_id>', methods=['GET'])
def get_history(record_id):
    """获取历史记录详情"""
    try:
        history_service = get_history_service()
        record = history_service.get_record(record_id)

        if not record:
            return jsonify({
                "success": False,
                "error": f"历史记录不存在：{record_id}\n可能原因：记录已被删除或ID错误"
            }), 404

        return jsonify({
            "success": True,
            "record": record
        }), 200

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"获取历史记录详情失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/history/<record_id>', methods=['PUT'])
def update_history(record_id):
    """更新历史记录"""
    try:
        data = request.get_json()
        outline = data.get('outline')
        images = data.get('images')
        status = data.get('status')
        thumbnail = data.get('thumbnail')

        history_service = get_history_service()
        success = history_service.update_record(
            record_id,
            outline=outline,
            images=images,
            status=status,
            thumbnail=thumbnail
        )

        if not success:
            return jsonify({
                "success": False,
                "error": f"更新历史记录失败：{record_id}\n可能原因：记录不存在或数据格式错误"
            }), 404

        return jsonify({
            "success": True
        }), 200

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"更新历史记录失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/history/<record_id>', methods=['DELETE'])
def delete_history(record_id):
    """删除历史记录"""
    try:
        history_service = get_history_service()
        success = history_service.delete_record(record_id)

        if not success:
            return jsonify({
                "success": False,
                "error": f"删除历史记录失败：{record_id}\n可能原因：记录不存在或ID错误"
            }), 404

        return jsonify({
            "success": True
        }), 200

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"删除历史记录失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/history/search', methods=['GET'])
def search_history():
    """搜索历史记录"""
    try:
        keyword = request.args.get('keyword', '')

        if not keyword:
            return jsonify({
                "success": False,
                "error": "参数错误：keyword 不能为空。\n请提供搜索关键词。"
            }), 400

        history_service = get_history_service()
        results = history_service.search_records(keyword)

        return jsonify({
            "success": True,
            "records": results
        }), 200

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"搜索历史记录失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/history/stats', methods=['GET'])
def get_history_stats():
    """获取历史记录统计"""
    try:
        history_service = get_history_service()
        stats = history_service.get_statistics()

        return jsonify({
            "success": True,
            **stats
        }), 200

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"获取历史记录统计失败。\n错误详情: {error_msg}"
        }), 500
