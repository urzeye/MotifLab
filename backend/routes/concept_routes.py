"""
概念可视化 API 路由

提供概念图生成的各步骤独立 API：
- POST /api/concept/analyze     分析文章提取概念
- POST /api/concept/map         映射概念到理论框架
- POST /api/concept/design      生成可视化设计方案
- POST /api/concept/generate    生成概念图图像
- POST /api/concept/run         完整流水线执行
- POST /api/concept/run/stream  完整流水线流式执行（SSE）
"""

import json
import logging
from flask import Blueprint, request, jsonify, Response, stream_with_context

from backend.skills.concept import (
    ConceptAnalyzeSkill,
    ConceptMapSkill,
    ConceptDesignSkill,
    ConceptGenerateSkill
)
from backend.skills.concept.analyze import AnalyzeInput
from backend.skills.concept.map_framework import MapInput
from backend.skills.concept.design import DesignInput
from backend.skills.concept.generate import GenerateInput
from backend.pipelines import ConceptPipeline
from backend.config import Config
from backend.services.concept_history import get_concept_history_service

logger = logging.getLogger(__name__)


def _get_provider_configs():
    """获取服务商配置"""
    config = {}
    try:
        text_provider = Config.get_active_text_provider()
        config['text_provider'] = Config.get_text_provider_config(text_provider)
    except Exception as e:
        logger.warning(f"获取文本服务商配置失败: {e}")
        config['text_provider'] = {}

    try:
        image_provider = Config.get_active_image_provider()
        config['image_provider'] = Config.get_image_provider_config(image_provider)
    except Exception as e:
        logger.warning(f"获取图片服务商配置失败: {e}")
        config['image_provider'] = {}

    return config


def create_concept_blueprint():
    """创建概念可视化蓝图"""
    bp = Blueprint('concept', __name__, url_prefix='/concept')

    @bp.route('/analyze', methods=['POST'])
    def analyze():
        """
        分析文章提取概念

        Request:
        {
            "article": "文章内容或文件路径",
            "max_concepts": 8  // 可选
        }

        Response:
        {
            "success": true,
            "data": {
                "main_theme": "主题",
                "key_concepts": [...],
                "relationships": [...]
            }
        }
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "error": "请求体不能为空"}), 400

            article = data.get('article', '')
            if not article:
                return jsonify({"success": False, "error": "缺少文章内容"}), 400

            max_concepts = data.get('max_concepts', 8)

            config = _get_provider_configs()
            skill = ConceptAnalyzeSkill(config=config)
            result = skill.run(AnalyzeInput(article=article, max_concepts=max_concepts))

            return jsonify({
                "success": result.success,
                "data": result.data,
                "message": result.message,
                "error": result.error
            })

        except Exception as e:
            logger.exception(f"分析失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route('/map', methods=['POST'])
    def map_framework():
        """
        映射概念到理论框架

        Request:
        {
            "concepts": [...] // analyze 的结果或概念列表
        }

        Response:
        {
            "success": true,
            "data": {
                "mappings": [...]
            }
        }
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "error": "请求体不能为空"}), 400

            concepts = data.get('concepts', data)

            config = _get_provider_configs()
            skill = ConceptMapSkill(config=config)
            result = skill.run(MapInput(concepts=concepts))

            return jsonify({
                "success": result.success,
                "data": result.data,
                "message": result.message,
                "error": result.error
            })

        except Exception as e:
            logger.exception(f"映射失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route('/design', methods=['POST'])
    def design():
        """
        生成可视化设计方案

        Request:
        {
            "mappings": [...], // map 的结果
            "style": "blueprint"  // 可选：视觉风格
        }

        Response:
        {
            "success": true,
            "data": {
                "designs": [...]
            }
        }
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "error": "请求体不能为空"}), 400

            mappings = data.get('mappings', data)
            style = data.get('style', 'blueprint')

            config = _get_provider_configs()
            skill = ConceptDesignSkill(config=config, style=style)
            result = skill.run(DesignInput(mappings=mappings, style=style))

            return jsonify({
                "success": result.success,
                "data": result.data,
                "message": result.message,
                "error": result.error
            })

        except Exception as e:
            logger.exception(f"设计失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route('/generate', methods=['POST'])
    def generate():
        """
        生成概念图图像

        Request:
        {
            "designs": [...],  // design 的结果
            "style": "blueprint",  // 可选
            "output_dir": "output/concepts/xxx"  // 可选
        }

        Response:
        {
            "success": true,
            "data": {
                "results": [...],
                "total": 5,
                "success_count": 5
            }
        }
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "error": "请求体不能为空"}), 400

            designs = data.get('designs', data)
            style = data.get('style', 'blueprint')
            output_dir = data.get('output_dir', 'output/concepts/default')

            config = _get_provider_configs()
            skill = ConceptGenerateSkill(config=config, style=style)
            result = skill.run(GenerateInput(
                designs=designs,
                style=style,
                output_dir=output_dir
            ))

            return jsonify({
                "success": result.success,
                "data": result.data,
                "message": result.message,
                "error": result.error
            })

        except Exception as e:
            logger.exception(f"生成失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route('/generate/stream', methods=['POST'])
    def generate_stream():
        """
        流式生成概念图图像（SSE）

        Request: 同 /generate

        Response: Server-Sent Events
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "error": "请求体不能为空"}), 400

            designs = data.get('designs', data)
            style = data.get('style', 'blueprint')
            output_dir = data.get('output_dir', 'output/concepts/default')

            def generate_events():
                config = _get_provider_configs()
                skill = ConceptGenerateSkill(config=config, style=style)

                try:
                    for event in skill.run_stream(GenerateInput(
                        designs=designs,
                        style=style,
                        output_dir=output_dir
                    )):
                        event_type = event.get('type', 'progress')
                        event_data = json.dumps(event, ensure_ascii=False)
                        yield f"event: {event_type}\ndata: {event_data}\n\n"
                except Exception as e:
                    logger.exception(f"流式生成异常: {e}")
                    error_data = json.dumps({
                        "type": "error",
                        "error": str(e)
                    }, ensure_ascii=False)
                    yield f"event: error\ndata: {error_data}\n\n"

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
            logger.exception(f"初始化失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route('/run', methods=['POST'])
    def run_pipeline():
        """
        执行完整概念图流水线

        Request:
        {
            "article": "文章内容",
            "style": "blueprint",  // 可选
            "config": {
                "skip_generate": false,  // 可选
                "max_concepts": 8  // 可选
            }
        }

        Response:
        {
            "success": true,
            "data": {
                "task_id": "xxx",
                "main_theme": "...",
                "concepts": [...],
                "mappings": [...],
                "designs": [...],
                "images": [...]
            }
        }
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "error": "请求体不能为空"}), 400

            config = _get_provider_configs()
            config['style'] = data.get('style', 'blueprint')
            if data.get('config'):
                config['pipeline'] = data['config']

            pipeline = ConceptPipeline(config=config)
            result = pipeline.run({
                'article': data.get('article', ''),
                'style': data.get('style', 'blueprint'),
                'config': data.get('config', {})
            })

            return jsonify({
                "success": result.success,
                "data": result.data,
                "message": result.message,
                "error": result.error
            })

        except Exception as e:
            logger.exception(f"流水线执行失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route('/run/stream', methods=['POST'])
    def run_pipeline_stream():
        """
        流式执行完整概念图流水线（SSE）

        Request: 同 /run

        Response: Server-Sent Events
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "error": "请求体不能为空"}), 400

            def generate_events():
                config = _get_provider_configs()
                config['style'] = data.get('style', 'blueprint')
                if data.get('config'):
                    config['pipeline'] = data['config']

                pipeline = ConceptPipeline(config=config)

                try:
                    for event in pipeline.run_stream({
                        'article': data.get('article', ''),
                        'style': data.get('style', 'blueprint'),
                        'config': data.get('config', {})
                    }):
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
                stream_with_context(generate_events()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no',
                }
            )

        except Exception as e:
            logger.exception(f"初始化失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    # ===== 历史记录 API =====

    @bp.route('/history', methods=['GET'])
    def list_history():
        """
        获取概念可视化历史记录列表

        Query params:
        - page: 页码，默认 1
        - page_size: 每页数量，默认 20
        - status: 状态过滤（可选）

        Response:
        {
            "success": true,
            "data": {
                "records": [...],
                "total": 10,
                "page": 1,
                "page_size": 20,
                "total_pages": 1
            }
        }
        """
        try:
            page = request.args.get('page', 1, type=int)
            page_size = request.args.get('page_size', 20, type=int)
            status = request.args.get('status', None)

            service = get_concept_history_service()
            result = service.list_records(page=page, page_size=page_size, status=status)

            return jsonify({
                "success": True,
                "data": result
            })

        except Exception as e:
            logger.exception(f"获取历史列表失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route('/history/<record_id>', methods=['GET'])
    def get_history_detail(record_id):
        """
        获取历史记录详情

        Response:
        {
            "success": true,
            "data": {
                "id": "xxx",
                "title": "...",
                "pipeline_data": {...},
                ...
            }
        }
        """
        try:
            service = get_concept_history_service()
            record = service.get_record(record_id)

            if not record:
                return jsonify({"success": False, "error": "记录不存在"}), 404

            return jsonify({
                "success": True,
                "data": record
            })

        except Exception as e:
            logger.exception(f"获取历史详情失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route('/history/<record_id>', methods=['DELETE'])
    def delete_history(record_id):
        """
        删除历史记录

        Response:
        {
            "success": true
        }
        """
        try:
            service = get_concept_history_service()
            success = service.delete_record(record_id)

            if not success:
                return jsonify({"success": False, "error": "删除失败或记录不存在"}), 404

            return jsonify({"success": True})

        except Exception as e:
            logger.exception(f"删除历史记录失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    return bp
