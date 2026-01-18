"""
内容生成技能

根据主题和大纲生成小红书风格的标题、文案和标签。
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from backend.core.base_skill import BaseSkill, SkillResult
from backend.clients.factory import ClientFactory

logger = logging.getLogger(__name__)


@dataclass
class ContentInput:
    """内容生成输入"""
    topic: str
    outline: str


class ContentSkill(BaseSkill):
    """
    内容生成技能

    输入：主题 + 大纲
    输出：标题列表、文案、标签列表
    """

    name = "content"
    description = "生成小红书标题、文案和标签"
    version = "2.0.0"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._client = None
        self._prompt_template = None

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

    @property
    def prompt_template(self) -> str:
        """延迟加载提示词模板"""
        if self._prompt_template is None:
            prompt_path = Path(__file__).parent.parent.parent / "prompts" / "content_prompt.txt"
            if prompt_path.exists():
                self._prompt_template = prompt_path.read_text(encoding='utf-8')
            else:
                logger.warning(f"提示词模板不存在: {prompt_path}")
                self._prompt_template = """请为以下小红书图文生成标题、文案和标签：

主题：{topic}
大纲：{outline}

请返回JSON格式：
{{"titles": ["标题1", "标题2"], "copywriting": "文案内容", "tags": ["标签1", "标签2"]}}"""
        return self._prompt_template

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """解析 AI 返回的 JSON 响应"""
        # 尝试直接解析
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # 尝试从 markdown 代码块中提取
        json_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', response_text)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 尝试找到 JSON 对象的开始和结束
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            try:
                return json.loads(response_text[start_idx:end_idx + 1])
            except json.JSONDecodeError:
                pass

        logger.error(f"无法解析 JSON 响应: {response_text[:200]}...")
        raise ValueError("AI 返回的内容格式不正确，无法解析")

    def get_required_inputs(self) -> List[str]:
        return ['topic', 'outline']

    def get_output_schema(self) -> Dict[str, Any]:
        return {
            'type': 'object',
            'properties': {
                'titles': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': '标题候选列表'
                },
                'copywriting': {
                    'type': 'string',
                    'description': '文案内容'
                },
                'tags': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': '标签列表'
                }
            }
        }

    def run(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> SkillResult:
        """
        执行内容生成

        Args:
            input_data: ContentInput 或包含 topic 和 outline 的字典
            context: 上下文信息

        Returns:
            SkillResult 包含标题、文案和标签
        """
        context = context or {}

        # 解析输入
        if isinstance(input_data, ContentInput):
            topic = input_data.topic
            outline = input_data.outline
        elif isinstance(input_data, dict):
            topic = input_data.get('topic', '')
            outline = input_data.get('outline', '')
        else:
            return SkillResult(
                success=False,
                error="输入格式错误，需要 topic 和 outline",
                metadata={'skill': self.name}
            )

        if not topic or not outline:
            return SkillResult(
                success=False,
                error="主题和大纲不能为空",
                metadata={'skill': self.name}
            )

        try:
            logger.info(f"开始生成内容: topic={topic[:50]}...")

            # 构建提示词
            prompt = self.prompt_template.format(topic=topic, outline=outline)

            # 获取模型参数
            provider_config = self.config.get('text_provider', {})
            model = provider_config.get('model', 'gemini-2.0-flash-exp')
            temperature = provider_config.get('temperature', 1.0)
            max_output_tokens = provider_config.get('max_output_tokens', 4000)

            # 调用 API
            logger.info(f"调用文本生成 API: model={model}")
            response_text = self.client.generate_text(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_output_tokens=max_output_tokens
            )

            # 解析响应
            content_data = self._parse_json_response(response_text)

            # 验证和规范化字段
            titles = content_data.get('titles', [])
            copywriting = content_data.get('copywriting', '')
            tags = content_data.get('tags', [])

            # 确保 titles 是列表
            if isinstance(titles, str):
                titles = [titles]

            # 确保 tags 是列表
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(',')]

            logger.info(f"内容生成完成: {len(titles)} 个标题, {len(tags)} 个标签")

            return SkillResult(
                success=True,
                data={
                    'titles': titles,
                    'copywriting': copywriting,
                    'tags': tags
                },
                metadata={
                    'skill': self.name,
                    'model': model,
                    'title_count': len(titles),
                    'tag_count': len(tags)
                }
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"内容生成失败: {error_msg}")

            if "api_key" in error_msg.lower() or "401" in error_msg:
                detailed_error = f"API 认证失败: {error_msg}"
            elif "model" in error_msg.lower() or "404" in error_msg:
                detailed_error = f"模型访问失败: {error_msg}"
            elif "rate" in error_msg.lower() or "429" in error_msg:
                detailed_error = f"API 配额限制: {error_msg}"
            else:
                detailed_error = f"内容生成失败: {error_msg}"

            return SkillResult(
                success=False,
                error=detailed_error,
                metadata={'skill': self.name}
            )
