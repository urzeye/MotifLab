"""
通用分析技能

提供文本分析能力，可用于：
- 提取关键概念和主题
- 识别文本结构和层次
- 分析内容类型和风格
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
class AnalyzeInput:
    """分析输入"""
    text: str
    analysis_type: str = "general"  # 'general', 'concept', 'structure'


class AnalyzeSkill(BaseSkill):
    """
    通用分析技能

    支持多种分析模式：
    - general: 通用文本分析
    - concept: 概念提取（用于概念图）
    - structure: 结构分析
    """

    name = "analyze"
    description = "分析文本内容，提取关键信息"
    version = "1.0.0"

    # 不同分析类型的提示词模板
    PROMPTS = {
        "general": """请分析以下文本，提取关键信息：

{text}

请返回JSON格式：
{{
    "summary": "简要总结",
    "keywords": ["关键词1", "关键词2"],
    "topics": ["主题1", "主题2"],
    "sentiment": "positive/negative/neutral",
    "word_count": 123
}}""",
        "concept": """请分析以下学术文本，提取核心概念：

{text}

请返回JSON格式：
{{
    "main_concept": "核心概念",
    "sub_concepts": ["子概念1", "子概念2"],
    "relationships": [
        {{"from": "概念A", "to": "概念B", "type": "包含/依赖/对比"}}
    ],
    "domain": "所属领域",
    "complexity": "basic/intermediate/advanced"
}}""",
        "structure": """请分析以下文本的结构：

{text}

请返回JSON格式：
{{
    "type": "article/list/dialogue/narrative",
    "sections": [
        {{"title": "章节标题", "summary": "章节摘要"}}
    ],
    "hierarchy_depth": 2,
    "has_introduction": true,
    "has_conclusion": true
}}"""
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

        # 尝试从 markdown 代码块提取
        json_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', response_text)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 尝试找到 JSON 对象
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            try:
                return json.loads(response_text[start_idx:end_idx + 1])
            except json.JSONDecodeError:
                pass

        raise ValueError("无法解析响应为 JSON")

    def get_required_inputs(self) -> List[str]:
        return ['text']

    def get_output_schema(self) -> Dict[str, Any]:
        return {
            'type': 'object',
            'properties': {
                'analysis_type': {'type': 'string'},
                'result': {'type': 'object'}
            }
        }

    def run(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> SkillResult:
        """
        执行文本分析

        Args:
            input_data: AnalyzeInput 或包含 text 和可选 analysis_type 的字典
            context: 上下文信息

        Returns:
            SkillResult 包含分析结果
        """
        context = context or {}

        # 解析输入
        if isinstance(input_data, AnalyzeInput):
            text = input_data.text
            analysis_type = input_data.analysis_type
        elif isinstance(input_data, dict):
            text = input_data.get('text', '')
            analysis_type = input_data.get('analysis_type', 'general')
        else:
            text = str(input_data)
            analysis_type = 'general'

        if not text:
            return SkillResult(
                success=False,
                error="待分析文本不能为空",
                metadata={'skill': self.name}
            )

        if analysis_type not in self.PROMPTS:
            analysis_type = 'general'

        try:
            logger.info(f"开始分析文本: type={analysis_type}, length={len(text)}")

            # 构建提示词
            prompt = self.PROMPTS[analysis_type].format(text=text)

            # 获取模型参数
            provider_config = self.config.get('text_provider', {})
            model = provider_config.get('model', 'gemini-2.0-flash-exp')
            temperature = provider_config.get('temperature', 0.7)
            max_output_tokens = provider_config.get('max_output_tokens', 4000)

            # 调用 API
            response_text = self.client.generate_text(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_output_tokens=max_output_tokens
            )

            # 解析响应
            result = self._parse_json_response(response_text)
            logger.info(f"文本分析完成: type={analysis_type}")

            return SkillResult(
                success=True,
                data={
                    'analysis_type': analysis_type,
                    'result': result
                },
                metadata={
                    'skill': self.name,
                    'model': model,
                    'input_length': len(text)
                }
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"文本分析失败: {error_msg}")

            return SkillResult(
                success=False,
                error=f"文本分析失败: {error_msg}",
                metadata={'skill': self.name}
            )
