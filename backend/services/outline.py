import logging
import os
import re
from typing import Dict, List, Any, Optional
from backend.config import Config
from backend.utils.text_client import get_text_chat_client

logger = logging.getLogger(__name__)


class OutlineService:
    def __init__(self):
        logger.debug("初始化 OutlineService...")
        # 加载完整文本配置（保留多服务商信息，便于按能力回退）
        self.text_config = Config.load_text_providers_config()
        # 启动时校验至少有一个可用服务商
        self._get_client()
        self.prompt_template = self._load_prompt_template()
        logger.info(f"OutlineService 初始化完成，使用服务商: {self.text_config.get('active_provider')}")

    def _is_provider_usable(self, provider_config: Dict[str, Any]) -> bool:
        """检查服务商配置是否可用（主要是 API Key）"""
        api_key = provider_config.get('api_key')
        if not api_key:
            return False
        if isinstance(api_key, str) and '${' in api_key and '}' in api_key:
            return False
        return True

    def _get_client(self, needs_image_support: bool = False):
        """根据配置获取客户端，必要时优先选择支持图片输入的服务商"""
        active_provider = self.text_config.get('active_provider', 'google_gemini')
        providers = self.text_config.get('providers', {})

        if not providers:
            logger.error("未找到任何文本生成服务商配置")
            raise ValueError(
                "未找到任何文本生成服务商配置。\n"
                "解决方案：\n"
                "1. 在系统设置页面添加文本生成服务商\n"
                "2. 或手动编辑 text_providers.yaml 文件"
            )

        ordered_provider_names = []
        if active_provider in providers:
            ordered_provider_names.append(active_provider)
        for name in providers.keys():
            if name != active_provider:
                ordered_provider_names.append(name)

        candidates = []
        for name in ordered_provider_names:
            provider_config = providers.get(name, {})
            if not self._is_provider_usable(provider_config):
                continue
            if needs_image_support and not provider_config.get('supports_images', True):
                continue
            candidates.append((name, provider_config))

        # 若无“支持图片”的候选，则降级到任意可用服务商（并提示）
        if needs_image_support and not candidates:
            logger.warning("未找到 supports_images=true 的可用文本服务商，降级使用默认可用服务商")
            for name in ordered_provider_names:
                provider_config = providers.get(name, {})
                if self._is_provider_usable(provider_config):
                    candidates.append((name, provider_config))

        if not candidates:
            available = ', '.join(providers.keys()) if providers else '无'
            raise ValueError(
                f"未找到可用的文本生成服务商配置。\n"
                f"可用的服务商: {available}\n"
                "解决方案：在系统设置中检查并填写有效 API Key"
            )

        provider_name, provider_config = candidates[0]
        logger.info(
            f"使用文本服务商: {provider_name} "
            f"(type={provider_config.get('type')}, supports_images={provider_config.get('supports_images', True)})"
        )
        return get_text_chat_client(provider_config), provider_name, provider_config

    def _load_prompt_template(self) -> str:
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "prompts",
            "outline_prompt.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _parse_outline(self, outline_text: str) -> List[Dict[str, Any]]:
        # 按 <page> 分割页面（兼容旧的 --- 分隔符）
        if '<page>' in outline_text:
            pages_raw = re.split(r'<page>', outline_text, flags=re.IGNORECASE)
        else:
            # 向后兼容：如果没有 <page> 则使用 ---
            pages_raw = outline_text.split("---")

        pages = []

        for index, page_text in enumerate(pages_raw):
            page_text = page_text.strip()
            if not page_text:
                continue

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

    def _build_source_reference(self, source_content: Optional[str]) -> str:
        """构造网页参考素材片段，避免超长输入导致模型失败。"""
        if not source_content:
            return ""

        content = source_content.strip()
        if not content:
            return ""

        max_chars = 12000
        if len(content) > max_chars:
            logger.info(f"网页参考内容过长（{len(content)} 字符），已截断到 {max_chars} 字符")
            content = content[:max_chars] + "\n\n...(网页正文过长，已截断)"

        return (
            "\n\n【网页参考素材】\n"
            "以下内容来自用户提供的网页正文，请优先吸收其中的关键观点、数据和案例，"
            "并在大纲中自然融合：\n\n"
            f"{content}"
        )

    def generate_outline(
        self,
        topic: str,
        images: Optional[List[bytes]] = None,
        source_content: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            logger.info(
                "开始生成大纲: "
                f"topic={topic[:50]}..., "
                f"images={len(images) if images else 0}, "
                f"has_source={bool(source_content)}"
            )
            needs_image_support = bool(images and len(images) > 0)
            client, selected_provider_name, provider_config = self._get_client(
                needs_image_support=needs_image_support
            )
            prompt = self.prompt_template.format(topic=topic)
            prompt += self._build_source_reference(source_content)

            if images and len(images) > 0:
                prompt += f"\n\n注意：用户提供了 {len(images)} 张参考图片，请在生成大纲时考虑这些图片的内容和风格。这些图片可能是产品图、个人照片或场景图，请根据图片内容来优化大纲，使生成的内容与图片相关联。"
                logger.debug(f"添加了 {len(images)} 张参考图片到提示词")

            model = provider_config.get('model', 'gemini-2.0-flash-exp')
            temperature = provider_config.get('temperature', 1.0)
            max_output_tokens = provider_config.get('max_output_tokens', 8000)

            logger.info(
                f"调用文本生成 API: provider={selected_provider_name}, model={model}, "
                f"temperature={temperature}, needs_image_support={needs_image_support}"
            )
            outline_text = client.generate_text(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                images=images
            )

            logger.debug(f"API 返回文本长度: {len(outline_text)} 字符")
            pages = self._parse_outline(outline_text)
            logger.info(f"大纲解析完成，共 {len(pages)} 页")

            return {
                "success": True,
                "outline": outline_text,
                "pages": pages,
                "has_images": images is not None and len(images) > 0
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"大纲生成失败: {error_msg}")

            # 根据错误类型提供更详细的错误信息
            if "api_key" in error_msg.lower() or "unauthorized" in error_msg.lower() or "401" in error_msg:
                detailed_error = (
                    f"API 认证失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. API Key 无效或已过期\n"
                    "2. API Key 没有访问该模型的权限\n"
                    "解决方案：在系统设置页面检查并更新 API Key"
                )
            elif "model" in error_msg.lower() or "404" in error_msg:
                detailed_error = (
                    f"模型访问失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. 模型名称不正确\n"
                    "2. 没有访问该模型的权限\n"
                    "解决方案：在系统设置页面检查模型名称配置"
                )
            elif "timeout" in error_msg.lower() or "连接" in error_msg:
                detailed_error = (
                    f"网络连接失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. 网络连接不稳定\n"
                    "2. API 服务暂时不可用\n"
                    "3. Base URL 配置错误\n"
                    "解决方案：检查网络连接，稍后重试"
                )
            elif "rate" in error_msg.lower() or "429" in error_msg or "quota" in error_msg.lower():
                detailed_error = (
                    f"API 配额限制。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. API 调用次数超限\n"
                    "2. 账户配额用尽\n"
                    "解决方案：等待配额重置，或升级 API 套餐"
                )
            else:
                detailed_error = (
                    f"大纲生成失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. Text API 配置错误或密钥无效\n"
                    "2. 网络连接问题\n"
                    "3. 模型无法访问或不存在\n"
                    "建议：检查配置文件 text_providers.yaml"
                )

            return {
                "success": False,
                "error": detailed_error
            }


def get_outline_service() -> OutlineService:
    """
    获取大纲生成服务实例
    每次调用都创建新实例以确保配置是最新的
    """
    return OutlineService()
