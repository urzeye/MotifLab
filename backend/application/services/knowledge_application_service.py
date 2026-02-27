"""知识库应用层服务。"""

from __future__ import annotations

from typing import Any, Dict, List

from backend.knowledge import registry

_knowledge_application_service: "KnowledgeApplicationService | None" = None


class KnowledgeApplicationService:
    """封装知识库查询与写入用例。"""

    def list_frameworks(self) -> List[Dict[str, Any]]:
        """获取并格式化理论框架列表。"""
        frameworks = registry.list_frameworks()
        formatted: List[Dict[str, Any]] = []
        for framework in frameworks:
            formatted.append(
                {
                    "id": framework.get("id"),
                    "name": framework.get("name", framework.get("name_en", "")),
                    "description": framework.get("description", ""),
                    "domains": framework.get("keywords", []),
                    "components": framework.get("visual_elements", []),
                    "use_when": framework.get("use_when", ""),
                    "canonical_chart": framework.get("canonical_chart"),
                    "suggested_charts": framework.get("suggested_charts", []),
                }
            )
        return formatted

    def create_framework(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建新理论框架。"""
        name = data.get("name")
        if not name:
            raise ValueError("框架名称不能为空")

        framework_id = str(name).lower().replace(" ", "_").replace("(", "").replace(")", "")
        framework_data = {
            "id": framework_id,
            "name": name,
            "description": data.get("description", ""),
            "keywords": data.get("keywords", data.get("domains", [])),
            "visual_elements": data.get("visual_elements", data.get("components", [])),
            "use_when": data.get("use_when", ""),
            "canonical_chart": data.get("canonical_chart"),
            "suggested_charts": data.get("suggested_charts", []),
        }
        registry.add_framework(framework_id, framework_data, persist=True)
        return framework_data

    def list_chart_types(self) -> List[Dict[str, Any]]:
        """获取并格式化图表类型列表。"""
        chart_types = registry.list_chart_types()
        formatted: List[Dict[str, Any]] = []
        for chart in chart_types:
            formatted.append(
                {
                    "id": chart.get("id"),
                    "name": chart.get("name", chart.get("name_en", "")),
                    "description": chart.get("description", ""),
                    "best_for": chart.get("best_for", []),
                }
            )
        return formatted

    def list_visual_styles(self) -> List[Dict[str, Any]]:
        """获取并格式化视觉风格列表。"""
        visual_styles = registry.list_visual_styles()
        formatted: List[Dict[str, Any]] = []
        for style in visual_styles:
            formatted.append(
                {
                    "id": style.get("id"),
                    "name": style.get("name", ""),
                    "description": style.get("description", ""),
                    "colors": style.get(
                        "colors",
                        {
                            "primary": "#2F337",
                            "secondary": "#8B7355",
                            "background": "#F5F0E1",
                        },
                    ),
                }
            )
        return formatted

    def reload_knowledge(self) -> Dict[str, Any]:
        """重新加载知识库并返回统计。"""
        registry.reload()
        return {
            "frameworks": len(registry.frameworks),
            "chart_types": len(registry.chart_types),
            "visual_styles": len(registry.visual_styles),
        }


def get_knowledge_application_service() -> KnowledgeApplicationService:
    """获取知识库应用层服务（单例）。"""
    global _knowledge_application_service
    if _knowledge_application_service is None:
        _knowledge_application_service = KnowledgeApplicationService()
    return _knowledge_application_service
