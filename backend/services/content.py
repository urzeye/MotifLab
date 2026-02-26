"""
内容生成服务

生成小红书风格的标题、文案和标签
"""

import json
import logging
import os
import re
from typing import Dict, List, Any, Optional
from backend.config import Config
from backend.utils.text_client import get_text_chat_client

logger = logging.getLogger(__name__)


class ContentService:
    """内容生成服务：生成标题、文案、标签"""

    def __init__(self):
        logger.debug("初始化 ContentService...")
        self.text_config = self._load_text_config()
        self.client, self.active_provider, self.active_provider_config = self._get_client()
        self.prompt_template = self._load_prompt_template()
        logger.info(f"ContentService 初始化完成，使用服务商: {self.active_provider}")

    def _load_text_config(self) -> dict:
        """加载文本生成配置（支持 .env 变量解析）。"""
        config = Config.load_text_providers_config()
        logger.debug(f"文本配置加载成功: active={config.get('active_provider')}")
        return config

    @staticmethod
    def _is_provider_usable(provider_config: Dict[str, Any]) -> bool:
        """检查服务商配置是否可用（主要是 API Key）。"""
        api_key = provider_config.get('api_key')
        if not api_key:
            return False
        if isinstance(api_key, str) and '${' in api_key and '}' in api_key:
            return False
        return True

    def _get_client(self) -> tuple[Any, str, Dict[str, Any]]:
        """根据配置获取可用客户端，优先 active_provider。"""
        active_provider = self.text_config.get('active_provider', 'google_gemini')
        providers = self.text_config.get('providers', {})

        if not providers:
            logger.error("未找到任何文本生成服务商配置")
            raise ValueError(
                "未找到任何文本生成服务商配置。\n"
                "解决方案：\n"
                "1. 在系统设置页面添加文本生成服务商\n"
                "2. 或检查当前配置存储中的文本服务商配置"
            )

        ordered_provider_names = []
        if active_provider in providers:
            ordered_provider_names.append(active_provider)
        for name in providers.keys():
            if name != active_provider:
                ordered_provider_names.append(name)

        for provider_name in ordered_provider_names:
            provider_config = providers.get(provider_name, {})
            if not self._is_provider_usable(provider_config):
                continue
            logger.info(f"使用文本服务商: {provider_name} (type={provider_config.get('type')})")
            return get_text_chat_client(provider_config), provider_name, provider_config

        available = ', '.join(providers.keys())
        logger.error(f"文本服务商均不可用: {available}")
        raise ValueError(
            "未找到可用的文本生成服务商（API Key 为空或未解析）。\n"
            f"当前服务商: {available}\n"
            "解决方案：在系统设置页面填写有效 API Key，或检查密钥配置是否正确"
        )

    def _load_prompt_template(self) -> str:
        """加载提示词模板"""
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "prompts",
            "content_prompt.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

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

    def generate_content(
        self,
        topic: str,
        outline: str
    ) -> Dict[str, Any]:
        """
        生成标题、文案和标签

        参数：
            topic: 用户输入的主题
            outline: 大纲内容

        返回：
            包含 titles, copywriting, tags 的字典
        """
        try:
            logger.info(f"开始生成内容: topic={topic[:50]}...")

            # 构建提示词
            prompt = self.prompt_template.format(
                topic=topic,
                outline=outline
            )

            # 从配置中获取模型参数
            model = self.active_provider_config.get('model', 'gemini-2.0-flash-exp')
            temperature = self.active_provider_config.get('temperature', 1.0)
            max_output_tokens = self.active_provider_config.get('max_output_tokens', 4000)

            logger.info(f"调用文本生成 API: model={model}, temperature={temperature}")
            response_text = self.client.generate_text(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_output_tokens=max_output_tokens
            )

            logger.debug(f"API 返回文本长度: {len(response_text)} 字符")

            # 解析 JSON 响应
            content_data = self._parse_json_response(response_text)

            # 验证必要字段
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

            return {
                "success": True,
                "titles": titles,
                "copywriting": copywriting,
                "tags": tags
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"内容生成失败: {error_msg}")

            # 根据错误类型提供更详细的错误信息
            if "api_key" in error_msg.lower() or "unauthorized" in error_msg.lower() or "401" in error_msg:
                detailed_error = (
                    f"API 认证失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：API Key 无效或已过期\n"
                    "解决方案：在系统设置页面检查并更新 API Key"
                )
            elif "model" in error_msg.lower() or "404" in error_msg:
                detailed_error = (
                    f"模型访问失败。\n"
                    f"错误详情: {error_msg}\n"
                    "解决方案：在系统设置页面检查模型名称配置"
                )
            elif "timeout" in error_msg.lower() or "连接" in error_msg:
                detailed_error = (
                    f"网络连接失败。\n"
                    f"错误详情: {error_msg}\n"
                    "解决方案：检查网络连接，稍后重试"
                )
            elif "rate" in error_msg.lower() or "429" in error_msg or "quota" in error_msg.lower():
                detailed_error = (
                    f"API 配额限制。\n"
                    f"错误详情: {error_msg}\n"
                    "解决方案：等待配额重置，或升级 API 套餐"
                )
            else:
                detailed_error = (
                    f"内容生成失败。\n"
                    f"错误详情: {error_msg}\n"
                    "建议：检查文本服务商配置（系统设置）"
                )

            return {
                "success": False,
                "error": detailed_error
            }


def get_content_service() -> ContentService:
    """
    获取内容生成服务实例
    每次调用都创建新实例以确保配置是最新的
    """
    return ContentService()
