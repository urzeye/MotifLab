"""
流水线 API 路由

提供统一的流水线执行接口，支持 SSE 流式响应。

API:
- POST /api/pipeline/run          同步执行流水线
- POST /api/pipeline/run/stream   流式执行流水线（SSE）
- GET  /api/pipeline/types        获取可用流水线类型
- POST /api/pipeline/cancel       取消正在执行的流水线
"""

import json
import logging
from flask import Blueprint, request, jsonify, Response, stream_with_context

from backend.services.pipeline_service import get_pipeline_service

logger = logging.getLogger(__name__)


def create_pipeline_blueprint():
    """创建流水线蓝图"""
    bp = Blueprint('pipeline', __name__, url_prefix='/pipeline')

    @bp.route('/types', methods=['GET'])
    def get_pipeline_types():
        """
        获取可用的流水线类型

        Response:
        {
            "pipelines": {
                "redbook": "小红书图文生成流水线",
                "concept": "概念图生成流水线"
            }
        }
        """
        try:
            service = get_pipeline_service()
            pipelines = service.get_available_pipelines()
            return jsonify({
                "success": True,
                "pipelines": pipelines
            })
        except Exception as e:
            logger.error(f"获取流水线类型失败: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @bp.route('/run', methods=['POST'])
    def run_pipeline():
        """
        同步执行流水线

        Request:
        {
            "pipeline": "redbook",
            "input": {
                "topic": "主题",
                "images": [...]  // 可选，base64 编码的图片
            },
            "config": {}  // 可选配置
        }

        Response:
        {
            "success": true,
            "data": { ... },
            "run_id": "xxx",
            "elapsed_time": 12.5
        }
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "error": "请求体不能为空"}), 400

            pipeline_type = data.get('pipeline', 'redbook')
            input_data = data.get('input', {})
            config = data.get('config', {})

            # 处理 base64 图片
            if 'images' in input_data and isinstance(input_data['images'], list):
                import base64
                decoded_images = []
                for img in input_data['images']:
                    if isinstance(img, str):
                        # 移除 data:image/xxx;base64, 前缀
                        if ',' in img:
                            img = img.split(',')[1]
                        decoded_images.append(base64.b64decode(img))
                input_data['images'] = decoded_images

            service = get_pipeline_service()
            result = service.run_pipeline(pipeline_type, input_data, config)

            return jsonify(result)

        except ValueError as e:
            logger.warning(f"流水线参数错误: {e}")
            return jsonify({"success": False, "error": str(e)}), 400
        except Exception as e:
            logger.exception(f"流水线执行失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route('/run/stream', methods=['POST'])
    def run_pipeline_stream():
        """
        流式执行流水线（SSE）

        Request: 同 /run

        Response: Server-Sent Events
            event: start
            data: {"pipeline": "redbook", "run_id": "xxx"}

            event: progress
            data: {"step": 1, "skill": "outline", "progress": 0.1}

            event: step_complete
            data: {"step": 1, "skill": "outline", "result": {...}}

            event: image_progress
            data: {"index": 0, "status": "generating"}

            event: image_complete
            data: {"index": 0, "image_url": "/api/images/xxx/0.png"}

            event: finish
            data: {"success": true, "data": {...}}
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "error": "请求体不能为空"}), 400

            pipeline_type = data.get('pipeline', 'redbook')
            input_data = data.get('input', {})
            config = data.get('config', {})

            # 处理 base64 图片
            if 'images' in input_data and isinstance(input_data['images'], list):
                import base64
                decoded_images = []
                for img in input_data['images']:
                    if isinstance(img, str):
                        if ',' in img:
                            img = img.split(',')[1]
                        decoded_images.append(base64.b64decode(img))
                input_data['images'] = decoded_images

            def generate():
                service = get_pipeline_service()
                try:
                    for event in service.run_pipeline_stream(pipeline_type, input_data, config):
                        event_dict = event.to_dict()
                        event_type = event_dict.get('event', 'message')
                        event_data = json.dumps(event_dict, ensure_ascii=False)
                        yield f"event: {event_type}\ndata: {event_data}\n\n"
                except Exception as e:
                    logger.exception(f"流水线流式执行异常: {e}")
                    error_data = json.dumps({
                        "event": "error",
                        "error": str(e)
                    }, ensure_ascii=False)
                    yield f"event: error\ndata: {error_data}\n\n"

            return Response(
                stream_with_context(generate()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no',  # 禁用 nginx 缓冲
                }
            )

        except ValueError as e:
            logger.warning(f"流水线参数错误: {e}")
            return jsonify({"success": False, "error": str(e)}), 400
        except Exception as e:
            logger.exception(f"流水线初始化失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route('/cancel', methods=['POST'])
    def cancel_pipeline():
        """
        取消正在执行的流水线

        Request:
        {
            "run_id": "xxx"
        }

        Response:
        {
            "success": true,
            "cancelled": true
        }
        """
        try:
            data = request.get_json()
            run_id = data.get('run_id')

            if not run_id:
                return jsonify({"success": False, "error": "缺少 run_id"}), 400

            service = get_pipeline_service()
            cancelled = service.cancel_pipeline(run_id)

            return jsonify({
                "success": True,
                "cancelled": cancelled
            })

        except Exception as e:
            logger.error(f"取消流水线失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    return bp
