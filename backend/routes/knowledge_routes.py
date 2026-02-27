"""
知识库 API 路由

提供知识库管理接口，用于管理理论框架、图表类型和视觉风格。

API:
- GET  /api/knowledge/frameworks       获取所有理论框架
- POST /api/knowledge/frameworks       创建新框架
- GET  /api/knowledge/chart-types      获取所有图表类型
- GET  /api/knowledge/visual-styles    获取所有视觉风格
- POST /api/knowledge/reload           重新加载知识库
"""

import logging
from flask import Blueprint, request
from backend.application.services import get_knowledge_application_service
from backend.interfaces.http import json_response

logger = logging.getLogger(__name__)
knowledge_application_service = get_knowledge_application_service()


def create_knowledge_blueprint():
    """创建知识库蓝图"""
    bp = Blueprint('knowledge', __name__, url_prefix='/knowledge')

    @bp.route('/frameworks', methods=['GET'])
    def get_frameworks():
        """
        获取所有理论框架

        Response:
        {
            "success": true,
            "frameworks": [
                {
                    "id": "framework_id",
                    "name": "框架名称",
                    "description": "框架描述",
                    "keywords": [...],
                    "visual_elements": [...],
                    "use_when": "适用场景",
                    "canonical_chart": "推荐图表",
                    "suggested_charts": [...]
                }
            ]
        }
        """
        try:
            formatted = knowledge_application_service.list_frameworks()

            return json_response({
                "success": True,
                "frameworks": formatted,
                "total": len(formatted)
            }, 200)

        except Exception as e:
            logger.error(f"获取框架列表失败: {e}")
            return json_response({"success": False, "error": str(e)}, 500)

    @bp.route('/frameworks', methods=['POST'])
    def create_framework():
        """
        创建新理论框架

        Request:
        {
            "name": "框架名称",
            "description": "框架描述",
            "keywords": ["关键词1"],
            "visual_elements": ["视觉元素1"],
            "use_when": "适用场景",
            "canonical_chart": "推荐图表类型"
        }
        """
        try:
            data = request.get_json(silent=True)
            if not data:
                return json_response({"success": False, "error": "请求体不能为空"}, 400)
            framework_data = knowledge_application_service.create_framework(data)
            logger.info(f"创建新框架: {framework_data.get('name')}")

            return json_response({
                "success": True,
                "message": "框架创建成功",
                "framework": framework_data
            }, 200)

        except ValueError as e:
            return json_response({"success": False, "error": str(e)}, 400)
        except Exception as e:
            logger.error(f"创建框架失败: {e}")
            return json_response({"success": False, "error": str(e)}, 500)

    @bp.route('/chart-types', methods=['GET'])
    def get_chart_types():
        """
        获取所有图表类型

        Response:
        {
            "success": true,
            "chart_types": [...]
        }
        """
        try:
            formatted = knowledge_application_service.list_chart_types()

            return json_response({
                "success": True,
                "chart_types": formatted,
                "total": len(formatted)
            }, 200)

        except Exception as e:
            logger.error(f"获取图表类型失败: {e}")
            return json_response({"success": False, "error": str(e)}, 500)

    @bp.route('/visual-styles', methods=['GET'])
    def get_visual_styles():
        """
        获取所有视觉风格

        Response:
        {
            "success": true,
            "visual_styles": [...]
        }
        """
        try:
            formatted = knowledge_application_service.list_visual_styles()

            return json_response({
                "success": True,
                "visual_styles": formatted,
                "total": len(formatted)
            }, 200)

        except Exception as e:
            logger.error(f"获取视觉风格失败: {e}")
            return json_response({"success": False, "error": str(e)}, 500)

    @bp.route('/reload', methods=['POST'])
    def reload_knowledge():
        """
        重新加载知识库

        用于在添加新 YAML 文件后刷新知识库
        """
        try:
            stats = knowledge_application_service.reload_knowledge()
            return json_response({
                "success": True,
                "message": "知识库已重新加载",
                "stats": stats
            }, 200)

        except Exception as e:
            logger.error(f"重新加载知识库失败: {e}")
            return json_response({"success": False, "error": str(e)}, 500)

    return bp
