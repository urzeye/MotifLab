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
from flask import Blueprint, request, jsonify
from backend.knowledge import registry

logger = logging.getLogger(__name__)


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
            frameworks = registry.list_frameworks()

            # 转换为前端期望的格式
            formatted = []
            for f in frameworks:
                formatted.append({
                    "id": f.get("id"),
                    "name": f.get("name", f.get("name_en", "")),
                    "description": f.get("description", ""),
                    "domains": f.get("keywords", []),  # 使用 keywords 作为 domains
                    "components": f.get("visual_elements", []),
                    "use_when": f.get("use_when", ""),
                    "canonical_chart": f.get("canonical_chart"),
                    "suggested_charts": f.get("suggested_charts", [])
                })

            return jsonify({
                "success": True,
                "frameworks": formatted,
                "total": len(formatted)
            })

        except Exception as e:
            logger.error(f"获取框架列表失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

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
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "error": "请求体不能为空"}), 400

            name = data.get('name')
            if not name:
                return jsonify({"success": False, "error": "框架名称不能为空"}), 400

            # 生成 ID
            framework_id = name.lower().replace(' ', '_').replace('(', '').replace(')', '')

            framework_data = {
                "id": framework_id,
                "name": name,
                "description": data.get('description', ''),
                "keywords": data.get('keywords', data.get('domains', [])),
                "visual_elements": data.get('visual_elements', data.get('components', [])),
                "use_when": data.get('use_when', ''),
                "canonical_chart": data.get('canonical_chart'),
                "suggested_charts": data.get('suggested_charts', [])
            }

            # 保存到注册表（持久化到YAML文件）
            registry.add_framework(framework_id, framework_data, persist=True)
            logger.info(f"创建新框架: {name}")

            return jsonify({
                "success": True,
                "message": "框架创建成功",
                "framework": framework_data
            })

        except Exception as e:
            logger.error(f"创建框架失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

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
            chart_types = registry.list_chart_types()

            # 转换为前端期望的格式
            formatted = []
            for c in chart_types:
                formatted.append({
                    "id": c.get("id"),
                    "name": c.get("name", c.get("name_en", "")),
                    "description": c.get("description", ""),
                    "best_for": c.get("best_for", [])
                })

            return jsonify({
                "success": True,
                "chart_types": formatted,
                "total": len(formatted)
            })

        except Exception as e:
            logger.error(f"获取图表类型失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

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
            visual_styles = registry.list_visual_styles()

            # 转换为前端期望的格式
            formatted = []
            for s in visual_styles:
                formatted.append({
                    "id": s.get("id"),
                    "name": s.get("name", ""),
                    "description": s.get("description", ""),
                    "colors": s.get("colors", {
                        "primary": "#2F337",
                        "secondary": "#8B7355",
                        "background": "#F5F0E1"
                    })
                })

            return jsonify({
                "success": True,
                "visual_styles": formatted,
                "total": len(formatted)
            })

        except Exception as e:
            logger.error(f"获取视觉风格失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route('/reload', methods=['POST'])
    def reload_knowledge():
        """
        重新加载知识库

        用于在添加新 YAML 文件后刷新知识库
        """
        try:
            registry.reload()
            return jsonify({
                "success": True,
                "message": "知识库已重新加载",
                "stats": {
                    "frameworks": len(registry.frameworks),
                    "chart_types": len(registry.chart_types),
                    "visual_styles": len(registry.visual_styles)
                }
            })

        except Exception as e:
            logger.error(f"重新加载知识库失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    return bp
