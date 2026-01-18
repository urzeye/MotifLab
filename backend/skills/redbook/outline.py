"""
大纲生成技能

将用户主题转换为结构化的小红书图文大纲。
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from backend.core.base_skill import BaseSkill, SkillResult
from backend.clients.factory import ClientFactory

logger = logging.getLogger(__name__)


@dataclass
class OutlineInput:
    """大纲生成输入"""
    topic: str
    images: Optional[List[bytes]] = None


@dataclass
class OutlinePage:
    """大纲页面"""
    index: int
    type: str  # 'cover', 'content', 'summary'
    content: str


class OutlineSkill(BaseSkill):
    """
    大纲生成技能

    输入：用户主题 + 可选参考图片
    输出：结构化的页面大纲
    """

    name = "outline"
    description = "生成小红书图文大纲"
    version = "2.0.0"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._client = None
        self._prompt_template = None

    def _validate_config(self) -> None:
        """验证配置"""
        if not self.config.get('text_provider'):
            logger.warning("未指定 text_provider 配置，将在运行时从默认配置获取")

    @property
    def client(self):
        """延迟加载客户端"""
        if self._client is None:
            provider_config = self.config.get('text_provider', {})
            if not provider_config:
                # 从全局配置获取
                from backend.config import Config
                provider_name = Config.get_active_text_provider()
                provider_config = Config.get_text_provider_config(provider_name)
            self._client = ClientFactory.create_text_client(provider_config)
        return self._client

    @property
    def prompt_template(self) -> str:
        """延迟加载提示词模板"""
        if self._prompt_template is None:
            prompt_path = Path(__file__).parent.parent.parent / "prompts" / "outline_prompt.txt"
            if prompt_path.exists():
                self._prompt_template = prompt_path.read_text(encoding='utf-8')
            else:
                logger.warning(f"提示词模板不存在: {prompt_path}")
                self._prompt_template = "请为以下主题生成小红书图文大纲：\n{topic}"
        return self._prompt_template

    def _parse_outline(self, outline_text: str) -> List[Dict[str, Any]]:
        """解析大纲文本为结构化页面"""
        # 按 <page> 分割页面（兼容旧的 --- 分隔符）
        if '<page>' in outline_text:
            pages_raw = re.split(r'<page>', outline_text, flags=re.IGNORECASE)
        else:
            pages_raw = outline_text.split("---")

        pages = []
        for index, page_text in enumerate(pages_raw):
            page_text = page_text.strip()
            if not page_text:
                continue

            # 解析页面类型
            page_type = "content"
            type_match = re.match(r"\[(\S+)\]", page_text)
            if type_match:
                type_cn = type_match.group(1)
                type_mapping = {
                    "封面": "cover",
                    "内容": "content",
                    "总结": "summary",
                }
                page_type = type_mapping.get(type_cn, "content")

            pages.append({
                "index": index,
                "type": page_type,
                "content": page_text
            })

        return pages

    def get_required_inputs(self) -> List[str]:
        return ['topic']

    def get_output_schema(self) -> Dict[str, Any]:
        return {
            'type': 'object',
            'properties': {
                'outline': {'type': 'string', 'description': '原始大纲文本'},
                'pages': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'index': {'type': 'integer'},
                            'type': {'type': 'string', 'enum': ['cover', 'content', 'summary']},
                            'content': {'type': 'string'}
                        }
                    }
                },
                'has_images': {'type': 'boolean'}
            }
        }

    def run(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> SkillResult:
        """
        执行大纲生成

        Args:
            input_data: OutlineInput 或包含 topic 和可选 images 的字典
            context: 上下文信息

        Returns:
            SkillResult 包含大纲和解析后的页面列表
        """
        context = context or {}

        # 解析输入
        if isinstance(input_data, OutlineInput):
            topic = input_data.topic
            images = input_data.images
        elif isinstance(input_data, dict):
            topic = input_data.get('topic', '')
            images = input_data.get('images')
        else:
            topic = str(input_data)
            images = None

        if not topic:
            return SkillResult(
                success=False,
                error="主题不能为空",
                metadata={'skill': self.name}
            )

        try:
            logger.info(f"开始生成大纲: topic={topic[:50]}..., images={len(images) if images else 0}")

            # 构建提示词
            prompt = self.prompt_template.format(topic=topic)
            if images and len(images) > 0:
                prompt += f"\n\n注意：用户提供了 {len(images)} 张参考图片，请在生成大纲时考虑这些图片的内容和风格。"

            # 获取模型参数
            provider_config = self.config.get('text_provider', {})
            model = provider_config.get('model', 'gemini-2.0-flash-exp')
            temperature = provider_config.get('temperature', 1.0)
            max_output_tokens = provider_config.get('max_output_tokens', 8000)

            # 调用 API
            logger.info(f"调用文本生成 API: model={model}")
            outline_text = self.client.generate_text(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                images=images
            )

            # 解析大纲
            pages = self._parse_outline(outline_text)
            logger.info(f"大纲生成完成，共 {len(pages)} 页")

            return SkillResult(
                success=True,
                data={
                    'outline': outline_text,
                    'pages': pages,
                    'has_images': images is not None and len(images) > 0
                },
                metadata={
                    'skill': self.name,
                    'model': model,
                    'page_count': len(pages)
                }
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"大纲生成失败: {error_msg}")

            # 错误分类
            if "api_key" in error_msg.lower() or "401" in error_msg:
                detailed_error = f"API 认证失败: {error_msg}"
            elif "model" in error_msg.lower() or "404" in error_msg:
                detailed_error = f"模型访问失败: {error_msg}"
            elif "rate" in error_msg.lower() or "429" in error_msg:
                detailed_error = f"API 配额限制: {error_msg}"
            else:
                detailed_error = f"大纲生成失败: {error_msg}"

            return SkillResult(
                success=False,
                error=detailed_error,
                metadata={'skill': self.name}
            )
