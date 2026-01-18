"""
ConceptMapSkill - 理论框架映射

将提取的概念映射到科学/哲学方法论框架
"""

import json
from dataclasses import dataclass
from typing import Union, List, Dict, Optional

from backend.core.base_skill import BaseSkill, SkillResult
from backend.clients.factory import ClientFactory
from backend.knowledge import registry


@dataclass
class MapInput:
    """映射技能输入"""
    concepts: Union[List[Dict], Dict]  # analyze 结果或概念列表


MAP_PROMPT = '''你是一个跨学科理论家，擅长将概念映射到科学和哲学框架。

**可用的理论框架库：**

{frameworks_desc}

**任务：**
对于每个输入的概念，选择1-2个最合适的理论框架进行映射，并：
1. 解释映射关系
2. 生成一个基于框架的新标题（全大写英文）
3. 提供理论框架带来的新洞察
4. 注意框架的推荐图表类型，如果框架有推荐图表，请在输出中包含

**输入概念：**
```json
{concepts}
```

**输出格式（必须是有效JSON）：**
```json
{{
  "mappings": [
    {{
      "concept_id": "原概念ID",
      "original_name": "原概念名称",
      "framework": "映射的理论框架ID",
      "framework_name": "理论框架名称",
      "mapping_explanation": "映射解释（中文）",
      "new_title": "THE NEW TITLE IN CAPS",
      "subtitle": "可选的副标题",
      "insight": "理论框架带来的新洞察（中文）",
      "visual_metaphor": "建议的视觉隐喻",
      "recommended_chart": "框架推荐的图表类型（如有）",
      "alternative_charts": ["备选图表类型1", "备选图表类型2"]
    }}
  ]
}}
```

请直接输出JSON，不要有任何其他文字。
'''


class ConceptMapSkill(BaseSkill):
    """理论框架映射技能"""

    name = "concept_map"
    description = "将概念映射到科学/哲学理论框架"

    def __init__(self, config=None):
        super().__init__(config)
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

    def run(self, input_data: MapInput) -> SkillResult:
        """
        映射概念到理论框架

        Args:
            input_data: 包含概念列表的输入

        Returns:
            包含映射结果的 SkillResult
        """
        concepts = input_data.concepts

        # 处理输入
        if isinstance(concepts, dict):
            if "key_concepts" in concepts:
                concepts = concepts["key_concepts"]

        if isinstance(concepts, str):
            concepts = json.loads(concepts)

        prompt = MAP_PROMPT.format(
            frameworks_desc=registry.get_frameworks_for_prompt(),
            concepts=json.dumps(concepts, ensure_ascii=False, indent=2)
        )

        try:
            response = self.text_client.generate(prompt)

            # 提取JSON
            result = self._extract_json(response)

            if result:
                # 补充图表推荐
                for mapping in result.get('mappings', []):
                    framework_id = mapping.get('framework')
                    if framework_id:
                        framework = registry.get_framework(framework_id)
                        if framework:
                            if not mapping.get('recommended_chart') and framework.get('canonical_chart'):
                                mapping['recommended_chart'] = framework['canonical_chart']
                            if not mapping.get('alternative_charts') and framework.get('suggested_charts'):
                                mapping['alternative_charts'] = framework['suggested_charts']

                return SkillResult(
                    success=True,
                    data=result,
                    message=f"完成 {len(result.get('mappings', []))} 个概念的框架映射"
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
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[0] if response.strip().startswith("{") else response.split("```")[1].split("```")[0]
            else:
                json_str = response

            json_str = json_str.strip()
            if json_str.endswith("```"):
                json_str = json_str[:-3].strip()

            return json.loads(json_str)

        except json.JSONDecodeError:
            return None

    def format_output(self, result: SkillResult) -> str:
        """格式化输出结果"""
        if not result.success:
            return f"映射失败: {result.error}"

        data = result.data
        lines = [
            "# 理论框架映射结果",
            ""
        ]

        for i, m in enumerate(data.get('mappings', []), 1):
            lines.extend([
                f"## {i}. {m.get('new_title', 'UNTITLED')}",
                f"**副标题**: {m.get('subtitle', 'N/A')}",
                "",
                f"**原概念**: {m.get('original_name')}",
                f"**理论框架**: {m.get('framework_name')} ({m.get('framework')})",
                "",
                f"**映射解释**: {m.get('mapping_explanation')}",
                "",
                f"**洞察**: {m.get('insight')}",
                "",
                f"**视觉隐喻**: {m.get('visual_metaphor')}",
            ])
            if m.get('recommended_chart'):
                lines.append(f"**推荐图表**: {m.get('recommended_chart')}")
            if m.get('alternative_charts'):
                lines.append(f"**备选图表**: {', '.join(m.get('alternative_charts'))}")
            lines.extend([
                "",
                "---",
                ""
            ])

        return "\n".join(lines)
