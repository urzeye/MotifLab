"""Google GenAI 图片生成器"""
import logging
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
from .base import ImageGeneratorBase
from ..utils.image_compressor import compress_image

logger = logging.getLogger(__name__)

# 错误模式映射表
ERROR_PATTERNS = [
    # (关键词列表, 子关键词, 错误消息)
    (["401", "unauthenticated"], ["api key", "not supported"],
     "❌ API Key 认证失败：Vertex AI 不支持 API Key\n请使用 Google AI Studio 的 API Key"),
    (["401", "unauthenticated"], None,
     "❌ API Key 认证失败\n检查 API Key 是否正确，获取地址: https://aistudio.google.com/app/apikey"),
    (["403", "permission_denied", "forbidden"], ["billing", "quota"],
     "❌ 权限被拒绝：计费未启用或配额不足"),
    (["403", "permission_denied", "forbidden"], ["region", "location"],
     "❌ 权限被拒绝：区域限制，尝试配置代理"),
    (["403", "permission_denied", "forbidden"], None,
     "❌ 权限被拒绝\n检查 API 权限或尝试其他模型"),
    (["404", "not_found", "not found"], ["model"],
     "❌ 模型不存在\n推荐: imagen-3.0-generate-002 或 gemini-2.0-flash-exp-image-generation"),
    (["404", "not_found", "not found"], None,
     "❌ 请求的资源不存在"),
    (["429", "resource_exhausted", "quota"], ["per minute", "rpm"],
     "⏳ 请求频率超限，稍等片刻后重试或关闭「高并发模式」"),
    (["429", "resource_exhausted", "quota"], ["per day", "daily"],
     "⏳ 每日配额已用尽，等待明天重置或升级计划"),
    (["429", "resource_exhausted", "quota"], None,
     "⏳ API 配额或速率限制，稍后再试"),
    (["400", "invalid_argument", "invalid"], ["image", "size", "large"],
     "❌ 图片尺寸过大，请上传更小的图片"),
    (["400", "invalid_argument", "invalid"], ["prompt", "content"],
     "❌ 提示词参数错误，尝试缩短或移除敏感内容"),
    (["400", "invalid_argument", "invalid"], None,
     "❌ 请求参数错误"),
    (["safety", "blocked", "filter"], None,
     "🛡️ 内容被安全过滤器拦截，修改提示词避免敏感内容"),
    (["could not generate", "unable to generate"], None,
     "❌ 模型无法生成图片，确认使用支持图片生成的模型"),
    (["500", "internal"], None,
     "⚠️ Google API 服务器内部错误，稍后重试"),
    (["503", "unavailable"], None,
     "⚠️ Google API 服务暂时不可用，稍后重试"),
    (["timeout", "timed out"], None,
     "⏱️ 请求超时，检查网络连接后重试"),
    (["connection", "network", "refused"], None,
     "🌐 网络连接错误，检查网络或配置代理"),
    (["ssl", "certificate"], None,
     "🔒 SSL/TLS 证书错误，检查系统时间或代理设置"),
]


def parse_genai_error(error: Exception) -> str:
    """解析 Google GenAI API 错误，返回用户友好的错误信息"""
    error_str = str(error).lower()
    error_original = str(error)

    for patterns, sub_patterns, message in ERROR_PATTERNS:
        if any(p in error_str for p in patterns):
            if sub_patterns is None or any(sp in error_str for sp in sub_patterns):
                return message

    return f"❌ API 调用失败\n{error_original[:300]}\n检查 API Key、网络连接或查看后端日志"


class GoogleGenAIGenerator(ImageGeneratorBase):
    """Google GenAI 图片生成器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        if not self.api_key:
            raise ValueError("Google GenAI API Key 未配置\n获取: https://aistudio.google.com/app/apikey")

        client_kwargs = {"api_key": self.api_key, "vertexai": False}
        self.is_vertexai = False

        if self.config.get('base_url'):
            client_kwargs["http_options"] = {
                "base_url": self.config['base_url'],
                "api_version": "v1beta"
            }

        self.client = genai.Client(**client_kwargs)
        self.safety_settings = [
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
        ]
        logger.info("GoogleGenAIGenerator 初始化完成")

    def validate_config(self) -> bool:
        return bool(self.api_key)

    def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "3:4",
        temperature: float = 1.0,
        model: str = "gemini-3-pro-image-preview",
        reference_image: Optional[bytes] = None,
        **kwargs
    ) -> bytes:
        """生成图片"""
        logger.info(f"Google GenAI 生成图片: model={model}, aspect_ratio={aspect_ratio}")

        parts = []

        if reference_image:
            compressed_ref = compress_image(reference_image, max_size_kb=200)
            parts.append(types.Part(inline_data=types.Blob(mime_type="image/png", data=compressed_ref)))
            parts.append(types.Part(text=f"""请参考上面这张图片的视觉风格（配色、排版、字体、装饰元素），生成风格一致的新图片。

新图片内容：{prompt}

要求：保持相同视觉风格和设计语言，配色协调，排版装饰统一，但内容按新要求生成。"""))
        else:
            parts.append(types.Part(text=prompt))

        contents = [types.Content(role="user", parts=parts)]

        image_config_kwargs = {"aspect_ratio": aspect_ratio}
        if self.is_vertexai:
            image_config_kwargs["output_mime_type"] = "image/png"

        generate_content_config = types.GenerateContentConfig(
            temperature=temperature,
            top_p=0.95,
            max_output_tokens=32768,
            response_modalities=["TEXT", "IMAGE"],
            safety_settings=self.safety_settings,
            image_config=types.ImageConfig(**image_config_kwargs),
        )

        image_data = None
        for chunk in self.client.models.generate_content_stream(
            model=model, contents=contents, config=generate_content_config
        ):
            if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                for part in chunk.candidates[0].content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        image_data = part.inline_data.data
                        break

        if not image_data:
            raise ValueError("❌ 图片生成失败：API 返回为空\n修改提示词避免敏感内容，或检查网络后重试")

        logger.info(f"✅ Google GenAI 图片生成成功: {len(image_data)} bytes")
        return image_data

    def get_supported_aspect_ratios(self) -> list:
        return ["1:1", "3:4", "4:3", "16:9", "9:16"]
