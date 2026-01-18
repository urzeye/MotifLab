"""
ConceptDesignSkill - 可视化设计

为每个概念设计具体的可视化方案和图像提示词
"""

import json
from dataclasses import dataclass
from typing import Union, List, Dict, Optional

from backend.core.base_skill import BaseSkill, SkillResult
from backend.clients.factory import ClientFactory
from backend.knowledge import registry


@dataclass
class DesignInput:
    """设计技能输入"""
    mappings: Union[List[Dict], Dict]  # map 结果或映射列表
    style: str = "blueprint"  # 视觉风格


DESIGN_PROMPT = '''你是一位专业的技术文档设计师，擅长创建概念可视化图。

**统一样式规范：**
{style_prefix}

**可用图表类型：**
{chart_types}

**⚠️ 图表选择优先级（重要）：**
为每个概念选择 chart_type 时，请按以下优先级：
1. **首选**：使用映射结果中的 `recommended_chart` 字段（如果有）
2. **备选**：如果 recommended_chart 不适合内容，从 `alternative_charts` 中选择
3. **自由选择**：只有在没有推荐或推荐不适合时，才从完整图表库自由选择

**输入的映射结果：**
```json
{mappings}
```

**任务：**
为每个概念设计图像提示词（英文）。

**输出JSON格式：**
```json
{{
  "designs": [
    {{
      "concept_id": "c1",
      "title": "中文标题(15字内)",
      "chart_type": "图表类型",
      "visual_elements": ["元素1", "元素2", "元素3"],
      "image_prompt": "Technical infographic. [描述主图和布局，80-120词]. 4K resolution."
    }}
  ]
}}
```

**规则：**
- image_prompt 必须英文，80-120词，以"Technical infographic."开头
- 只输出JSON，无其他文字
'''


class ConceptDesignSkill(BaseSkill):
    """可视化设计技能"""

    name = "concept_design"
    description = "设计图像提示词和视觉方案"

    def __init__(self, config=None, style: str = "blueprint"):
        super().__init__(config)
        self.style_id = style
        self._text_client = None

    @property
    def text_client(self):
        """延迟加载文本生成客户端"""
        if self._text_client is None:
            provider_config = self.config.get('text_provider', {})
            if not provider_config:
                from backend.config import Config
                provider_name = Config.get_active_text_provider()
                provider_config = Config.get_text_provider_config(provider_name)
            self._text_client = ClientFactory.create_text_client(provider_config)
        return self._text_client

    def run(self, input_data: DesignInput) -> SkillResult:
        """
        设计可视化方案

        Args:
            input_data: 包含映射结果的输入

        Returns:
            包含设计结果的 SkillResult
        """
        mappings = input_data.mappings
        self.style_id = input_data.style or "blueprint"

        if isinstance(mappings, dict):
            if "mappings" in mappings:
                mappings = mappings["mappings"]

        if isinstance(mappings, str):
            mappings = json.loads(mappings)

        style = registry.get_visual_style(self.style_id)
        style_prefix = style.get("style_prefix", style.get("template", ""))

        prompt = DESIGN_PROMPT.format(
            style_prefix=style_prefix,
            chart_types=registry.get_chart_types_for_prompt(),
            mappings=json.dumps(mappings, ensure_ascii=False, indent=2)
        )

        try:
            response = self.text_client.generate_text(prompt, max_output_tokens=16000)

            # 提取JSON
            result = self._extract_json(response)

            if result:
                return SkillResult(
                    success=True,
                    data=result,
                    message=f"完成 {len(result.get('designs', []))} 个可视化设计"
                )
            else:
                return SkillResult(
                    success=False,
                    data={"raw_response": response},
                    error="JSON解析失败"
                )

        except Exception as e:
            return SkillResult(
                success=False,
                error=str(e)
            )

    def _extract_json(self, response: str) -> Optional[dict]:
        """从响应中提取JSON"""
        import re
        import logging
        logger = logging.getLogger(__name__)

        # 策略1: 直接解析
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass

        # 策略2: 提取 ```json ... ``` 块
        if "```json" in response:
            try:
                json_str = response.split("```json")[1].split("```")[0]
                return json.loads(json_str.strip())
            except (json.JSONDecodeError, IndexError):
                pass

        # 策略3: 提取 ``` ... ``` 块
        if "```" in response:
            try:
                json_str = response.split("```")[1].split("```")[0]
                return json.loads(json_str.strip())
            except (json.JSONDecodeError, IndexError):
                pass

        # 策略4: 使用正则查找 JSON 对象
        try:
            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                return json.loads(match.group())
        except json.JSONDecodeError:
            pass

        logger.warning(f"无法从响应中提取JSON，响应内容: {response[:1000]}")
        return None

    def format_output(self, result: SkillResult) -> str:
        """格式化输出结果"""
        if not result.success:
            return f"设计失败: {result.error}"

        data = result.data
        lines = [
            "# 可视化设计方案",
            ""
        ]

        for i, d in enumerate(data.get('designs', []), 1):
            lines.extend([
                f"## {i}. {d.get('title', 'UNTITLED')}",
                "",
                f"**图表类型**: {d.get('chart_type')}",
                f"**布局**: {d.get('layout')}",
                "",
                "**视觉元素**:",
                *[f"- {e}" for e in d.get('visual_elements', [])],
                "",
                "**文字框**:",
                *[f"- [{t.get('label')}]: {t.get('content')[:50]}..." for t in d.get('text_boxes', [])],
                "",
                "**图像提示词**:",
                "```",
                d.get('image_prompt', 'N/A')[:200] + "...",
                "```",
                "",
                "---",
                ""
            ])

        return "\n".join(lines)

    def get_prompts_only(self, result: SkillResult) -> List[Dict]:
        """仅提取图像提示词列表"""
        if not result.success:
            return []

        prompts = []
        for d in result.data.get('designs', []):
            prompts.append({
                "title": d.get('title'),
                "prompt": d.get('image_prompt')
            })
        return prompts
