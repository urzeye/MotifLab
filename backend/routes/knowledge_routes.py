"""
知识库 API 路由

提供知识库管理接口，用于管理理论框架、图表类型和视觉风格。
（预留给 Concept Visualizer 迁移后使用）

API:
- GET  /api/knowledge/frameworks       获取所有理论框架
- POST /api/knowledge/frameworks       创建新框架
- GET  /api/knowledge/chart-types      获取所有图表类型
- GET  /api/knowledge/visual-styles    获取所有视觉风格
"""

import logging
from flask import Blueprint, request, jsonify

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
                    "domains": ["领域1", "领域2"],
                    "components": [...]
                }
            ]
        }
        """
        try:
            # TODO: 从 knowledge/registry.py 获取框架
            # 目前返回占位数据
            frameworks = [
                {
                    "id": "causal_loop",
                    "name": "因果回路图",
                    "description": "展示变量之间的因果关系和反馈回路",
                    "domains": ["系统思维", "管理学"],
                    "components": ["变量", "因果链接", "反馈回路"]
                },
                {
                    "id": "concept_hierarchy",
                    "name": "概念层次图",
                    "description": "展示概念之间的层次关系",
                    "domains": ["教育", "知识管理"],
                    "components": ["核心概念", "子概念", "关联"]
                },
                {
                    "id": "flow_diagram",
                    "name": "流程图",
                    "description": "展示过程或算法的步骤流程",
                    "domains": ["工程", "计算机科学"],
                    "components": ["开始/结束", "处理", "判断", "连接"]
                }
            ]

            return jsonify({
                "success": True,
                "frameworks": frameworks,
                "total": len(frameworks)
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
            "domains": ["领域1"],
            "components": ["组件1", "组件2"]
        }
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"success": False, "error": "请求体不能为空"}), 400

            name = data.get('name')
            if not name:
                return jsonify({"success": False, "error": "框架名称不能为空"}), 400

            # TODO: 保存到 knowledge/frameworks/ 目录
            # 目前返回占位响应
            logger.info(f"创建新框架: {name}")

            return jsonify({
                "success": True,
                "message": "框架创建成功（功能开发中）",
                "framework": {
                    "id": f"custom_{name.lower().replace(' ', '_')}",
                    "name": name,
                    "description": data.get('description', ''),
                    "domains": data.get('domains', []),
                    "components": data.get('components', [])
                }
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
            # TODO: 从 knowledge/chart_types/ 加载
            chart_types = [
                {
                    "id": "mind_map",
                    "name": "思维导图",
                    "description": "以中心主题向外发散的树状结构",
                    "best_for": ["头脑风暴", "笔记整理", "知识梳理"]
                },
                {
                    "id": "flowchart",
                    "name": "流程图",
                    "description": "展示步骤和决策的流程",
                    "best_for": ["算法", "业务流程", "工作流"]
                },
                {
                    "id": "venn_diagram",
                    "name": "维恩图",
                    "description": "展示集合之间的关系",
                    "best_for": ["比较", "分类", "概念关系"]
                },
                {
                    "id": "timeline",
                    "name": "时间线",
                    "description": "按时间顺序展示事件",
                    "best_for": ["历史", "项目规划", "发展过程"]
                }
            ]

            return jsonify({
                "success": True,
                "chart_types": chart_types,
                "total": len(chart_types)
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
            # TODO: 从 knowledge/visual_styles/ 加载
            visual_styles = [
                {
                    "id": "blueprint",
                    "name": "蓝图风格",
                    "description": "深蓝背景，白色线条，技术感",
                    "colors": {
                        "primary": "#1a365d",
                        "secondary": "#ffffff",
                        "background": "#0a192f"
                    }
                },
                {
                    "id": "minimal",
                    "name": "极简风格",
                    "description": "白色背景，黑色文字，简洁线条",
                    "colors": {
                        "primary": "#1a1a1a",
                        "secondary": "#666666",
                        "background": "#ffffff"
                    }
                },
                {
                    "id": "colorful",
                    "name": "多彩风格",
                    "description": "鲜艳配色，活泼，适合教育内容",
                    "colors": {
                        "primary": "#ff6b6b",
                        "secondary": "#4ecdc4",
                        "background": "#f7f7f7"
                    }
                },
                {
                    "id": "corporate",
                    "name": "商务风格",
                    "description": "专业配色，清晰层次，适合报告",
                    "colors": {
                        "primary": "#2563eb",
                        "secondary": "#64748b",
                        "background": "#f8fafc"
                    }
                }
            ]

            return jsonify({
                "success": True,
                "visual_styles": visual_styles,
                "total": len(visual_styles)
            })

        except Exception as e:
            logger.error(f"获取视觉风格失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    return bp
