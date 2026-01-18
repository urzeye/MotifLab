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


ANALYZE_PROMPT = '''分析文章，提取3-4个核心概念。

可视化类型: hierarchy/comparison/network/flowchart

输出JSON格式:
```json
{{
  "main_theme": "主题(20字内)",
  "key_concepts": [
    {{
      "id": "c1",
      "name": "EnglishName",
      "name_cn": "中文名",
      "description": "描述(30字内)",
      "key_quote": "引文(50字内)",
      "visualization_type": "hierarchy",
      "importance": 10
    }}
  ],
  "relationships": []
}}
```

文章:
{article}

直接输出JSON:
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
            response = self.text_client.generate_text(prompt, max_output_tokens=16000)

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
        import re
        import logging
        logger = logging.getLogger(__name__)

        # 记录原始响应（截取前500字符）
        logger.debug(f"LLM原始响应: {response[:500]}...")

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
            # 查找第一个 { 到最后一个 } 之间的内容
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
