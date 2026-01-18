"""
ConceptAnalyzeSkill - 分析文章提取核心概念

从文章中提取核心概念、关键引文和层级关系
"""

import json
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from backend.core.base_skill import BaseSkill, SkillResult
from backend.clients.factory import ClientFactory


@dataclass
class AnalyzeInput:
    """分析技能输入"""
    article: str  # 文章内容或文件路径
    max_concepts: int = 8  # 最大提取概念数


ANALYZE_PROMPT = '''你是一个概念分析专家。请分析以下文章，提取核心要点。

**任务：**
1. 识别文章的核心主题和论点
2. 提取5-8个关键概念
3. 为每个概念找出文章中最有力的原文引文
4. 识别概念之间的层级关系或逻辑关系
5. 为每个概念推荐适合的可视化类型

**可视化类型选项：**
- hierarchy: 层级/优先级概念 → 金字塔图
- comparison: 二元对比概念 → 对比图
- network: 系统/关系概念 → 网络图
- flowchart: 过程/决策概念 → 流程图
- terrain: 优化/权衡概念 → 地形图
- attractor: 吸引/趋向概念 → 吸引子图

**输出格式（必须是有效JSON）：**
```json
{{
  "main_theme": "文章主题的一句话总结",
  "key_concepts": [
    {{
      "id": "concept_1",
      "name": "概念名称（简短英文）",
      "name_cn": "概念中文名称",
      "description": "概念描述（1-2句话）",
      "key_quote": "原文引文（英文）",
      "visualization_type": "hierarchy|comparison|network|flowchart|terrain|attractor",
      "importance": 1-10
    }}
  ],
  "relationships": [
    {{
      "from": "concept_id",
      "to": "concept_id",
      "type": "contains|constrains|enables|contrasts"
    }}
  ]
}}
```

**文章内容：**
---
{article}
---

请直接输出JSON，不要有任何其他文字。
'''


class ConceptAnalyzeSkill(BaseSkill):
    """分析文章提取概念的技能"""

    name = "concept_analyze"
    description = "分析文章，提取核心概念和关键引文"

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

    def run(self, input_data: AnalyzeInput) -> SkillResult:
        """
        分析文章

        Args:
            input_data: 包含文章内容的输入

        Returns:
            包含分析结果的 SkillResult
        """
        article = input_data.article

        # 如果是文件路径，读取文件
        if article.endswith('.md') or article.endswith('.txt'):
            path = Path(article)
            if path.exists():
                article = path.read_text(encoding='utf-8')

        # 限制长度
        article = article[:15000]

        prompt = ANALYZE_PROMPT.format(article=article)

        try:
            response = self.text_client.generate(prompt)

            # 提取JSON
            result = self._extract_json(response)

            if result:
                return SkillResult(
                    success=True,
                    data=result,
                    message=f"提取了 {len(result.get('key_concepts', []))} 个核心概念"
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
            # 尝试找到JSON块
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            else:
                json_str = response

            return json.loads(json_str.strip())

        except json.JSONDecodeError:
            return None

    def format_output(self, result: SkillResult) -> str:
        """格式化输出结果"""
        if not result.success:
            return f"分析失败: {result.error}"

        data = result.data
        lines = [
            f"# 文章分析结果",
            f"",
            f"## 主题",
            f"{data.get('main_theme', 'N/A')}",
            f"",
            f"## 核心概念 ({len(data.get('key_concepts', []))}个)",
            ""
        ]

        for i, concept in enumerate(data.get('key_concepts', []), 1):
            lines.extend([
                f"### {i}. {concept.get('name_cn', concept.get('name'))}",
                f"- **英文名**: {concept.get('name')}",
                f"- **描述**: {concept.get('description')}",
                f"- **可视化**: {concept.get('visualization_type')}",
                f"- **引文**: \"{concept.get('key_quote', 'N/A')[:100]}...\"",
                ""
            ])

        return "\n".join(lines)
