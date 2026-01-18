"""
通用设计技能

生成可视化设计方案，用于：
- 概念图布局设计
- 图表类型选择
- 视觉风格推荐
"""

import logging
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from backend.core.base_skill import BaseSkill, SkillResult
from backend.clients.factory import ClientFactory

logger = logging.getLogger(__name__)


@dataclass
class DesignInput:
    """设计输入"""
    content: Dict[str, Any]  # 分析结果或概念数据
    design_type: str = "concept_map"  # 'concept_map', 'infographic', 'diagram'
    style_preference: Optional[str] = None  # 'blueprint', 'minimal', 'colorful'


class DesignSkill(BaseSkill):
    """
    通用设计技能

    根据内容生成可视化设计方案，包括：
    - 布局结构
    - 元素排列
    - 颜色方案
    - 字体建议
    """

    name = "design"
    description = "生成可视化设计方案"
    version = "1.0.0"

    # 设计类型的提示词模板
    PROMPTS = {
        "concept_map": """基于以下概念分析结果，设计一个概念图：

{content}

视觉风格偏好：{style}

请返回JSON格式的设计方案：
{{
    "layout": {{
        "type": "hierarchical/radial/force-directed",
        "direction": "top-down/left-right",
        "spacing": "compact/balanced/spacious"
    }},
    "nodes": [
        {{
            "id": "node1",
            "label": "概念名称",
            "type": "main/sub/detail",
            "position_hint": "center/top/bottom",
            "style": {{
                "shape": "rectangle/circle/diamond",
                "color": "#hexcode",
                "size": "large/medium/small"
            }}
        }}
    ],
    "edges": [
        {{
            "from": "node1",
            "to": "node2",
            "label": "关系描述",
            "style": {{
                "type": "solid/dashed/dotted",
                "arrow": "none/forward/both"
            }}
        }}
    ],
    "color_scheme": {{
        "primary": "#hexcode",
        "secondary": "#hexcode",
        "background": "#hexcode",
        "text": "#hexcode"
    }},
    "typography": {{
        "title_font": "sans-serif/serif",
        "body_font": "sans-serif/serif",
        "title_size": 24,
        "body_size": 14
    }}
}}""",
        "infographic": """基于以下内容，设计一个信息图：

{content}

视觉风格偏好：{style}

请返回JSON格式的设计方案：
{{
    "layout": {{
        "type": "vertical/horizontal/grid",
        "sections": 3,
        "aspect_ratio": "16:9/4:3/1:1"
    }},
    "sections": [
        {{
            "title": "章节标题",
            "type": "text/chart/icon-list/statistic",
            "content_hint": "内容提示"
        }}
    ],
    "visual_elements": [
        {{
            "type": "icon/chart/image",
            "description": "元素描述",
            "position": "section_index"
        }}
    ],
    "color_scheme": {{
        "primary": "#hexcode",
        "accent": "#hexcode",
        "background": "#hexcode"
    }}
}}""",
        "diagram": """基于以下内容，设计一个图表：

{content}

视觉风格偏好：{style}

请返回JSON格式的设计方案：
{{
    "chart_type": "flowchart/sequence/class/state",
    "elements": [
        {{
            "id": "elem1",
            "type": "process/decision/start/end",
            "label": "标签"
        }}
    ],
    "connections": [
        {{
            "from": "elem1",
            "to": "elem2",
            "label": "连接说明"
        }}
    ],
    "style": {{
        "theme": "light/dark",
        "rounded": true,
        "shadows": false
    }}
}}"""
    }

    # 预设视觉风格
    STYLES = {
        "blueprint": "蓝图风格：深蓝背景，白色线条，技术感",
        "minimal": "极简风格：白色背景，黑色文字，简洁线条",
        "colorful": "多彩风格：鲜艳配色，活泼，适合教育内容",
        "corporate": "商务风格：专业配色，清晰层次，适合报告",
        "academic": "学术风格：中性配色，严谨布局，适合论文"
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._client = None

    @property
    def client(self):
        """延迟加载客户端"""
        if self._client is None:
            provider_config = self.config.get('text_provider', {})
            if not provider_config:
                from backend.config import Config
                provider_name = Config.get_active_text_provider()
                provider_config = Config.get_text_provider_config(provider_name)
            self._client = ClientFactory.create_text_client(provider_config)
        return self._client

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """解析 JSON 响应"""
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', response_text)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            try:
                return json.loads(response_text[start_idx:end_idx + 1])
            except json.JSONDecodeError:
                pass

        raise ValueError("无法解析响应为 JSON")

    def get_required_inputs(self) -> List[str]:
        return ['content']

    def get_output_schema(self) -> Dict[str, Any]:
        return {
            'type': 'object',
            'properties': {
                'design_type': {'type': 'string'},
                'style': {'type': 'string'},
                'design': {'type': 'object'}
            }
        }

    def run(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> SkillResult:
        """
        执行设计生成

        Args:
            input_data: DesignInput 或包含 content 的字典
            context: 上下文信息

        Returns:
            SkillResult 包含设计方案
        """
        context = context or {}

        # 解析输入
        if isinstance(input_data, DesignInput):
            content = input_data.content
            design_type = input_data.design_type
            style_preference = input_data.style_preference
        elif isinstance(input_data, dict):
            content = input_data.get('content', {})
            design_type = input_data.get('design_type', 'concept_map')
            style_preference = input_data.get('style_preference')
        else:
            return SkillResult(
                success=False,
                error="输入格式错误，需要 content 字段",
                metadata={'skill': self.name}
            )

        if not content:
            return SkillResult(
                success=False,
                error="内容不能为空",
                metadata={'skill': self.name}
            )

        if design_type not in self.PROMPTS:
            design_type = 'concept_map'

        # 确定视觉风格
        style = style_preference or 'minimal'
        style_desc = self.STYLES.get(style, self.STYLES['minimal'])

        try:
            logger.info(f"开始生成设计方案: type={design_type}, style={style}")

            # 将内容转为字符串
            content_str = json.dumps(content, ensure_ascii=False, indent=2) if isinstance(content, dict) else str(content)

            # 构建提示词
            prompt = self.PROMPTS[design_type].format(
                content=content_str,
                style=style_desc
            )

            # 获取模型参数
            provider_config = self.config.get('text_provider', {})
            model = provider_config.get('model', 'gemini-2.0-flash-exp')
            temperature = provider_config.get('temperature', 0.8)
            max_output_tokens = provider_config.get('max_output_tokens', 4000)

            # 调用 API
            response_text = self.client.generate_text(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_output_tokens=max_output_tokens
            )

            # 解析响应
            design = self._parse_json_response(response_text)
            logger.info(f"设计方案生成完成: type={design_type}")

            return SkillResult(
                success=True,
                data={
                    'design_type': design_type,
                    'style': style,
                    'design': design
                },
                metadata={
                    'skill': self.name,
                    'model': model
                }
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"设计方案生成失败: {error_msg}")

            return SkillResult(
                success=False,
                error=f"设计方案生成失败: {error_msg}",
                metadata={'skill': self.name}
            )

    @classmethod
    def get_available_styles(cls) -> Dict[str, str]:
        """获取可用的视觉风格列表"""
        return cls.STYLES.copy()

    @classmethod
    def get_available_design_types(cls) -> List[str]:
        """获取可用的设计类型列表"""
        return list(cls.PROMPTS.keys())
