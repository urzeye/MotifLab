"""Text API 客户端封装"""
import os
import time
import random
import base64
import requests
from functools import wraps
from typing import List, Optional, Union
from dotenv import load_dotenv
from .image_compressor import compress_image

load_dotenv()


def retry_on_429(max_retries=3, base_delay=2):
    """429 错误自动重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "rate" in error_str.lower():
                        if attempt < max_retries - 1:
                            wait_time = (base_delay ** attempt) + random.uniform(0, 1)
                            print(f"[重试] 遇到限流，{wait_time:.1f}秒后重试 (尝试 {attempt + 2}/{max_retries})")
                            time.sleep(wait_time)
                            continue
                    raise
            raise Exception(
                f"Text API 重试 {max_retries} 次后仍失败。\n"
                "可能原因：\n"
                "1. API持续限流或配额不足\n"
                "2. 网络连接持续不稳定\n"
                "3. API服务暂时不可用\n"
                "建议：稍后再试，或联系API服务提供商"
            )
        return wrapper
    return decorator


class TextChatClient:
    """Text API 客户端封装类"""

    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv("TEXT_API_KEY") or os.getenv("BLTCY_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Text API Key 未配置。\n"
                "解决方案：\n"
                "1. 在项目根目录的 .env 文件中添加:\n"
                "   TEXT_API_KEY=你的API密钥\n"
                "   或 BLTCY_API_KEY=你的API密钥\n"
                "2. 或在代码中通过参数传入 api_key\n"
                "3. 重启应用使环境变量生效"
            )

        self.base_url = base_url or os.getenv("TEXT_API_BASE_URL", "https://api.example.com")
        self.chat_endpoint = f"{self.base_url}/v1/chat/completions"

    def _encode_image_to_base64(self, image_data: bytes) -> str:
        """将图片数据编码为 base64"""
        return base64.b64encode(image_data).decode('utf-8')

    def _build_content_with_images(
        self,
        text: str,
        images: List[Union[bytes, str]] = None
    ) -> Union[str, List[dict]]:
        """
        构建包含图片的 content

        Args:
            text: 文本内容
            images: 图片列表，可以是 bytes（图片数据）或 str（URL）

        Returns:
            如果没有图片，返回纯文本；有图片则返回多模态内容列表
        """
        if not images:
            return text

        content = [{"type": "text", "text": text}]

        for img in images:
            if isinstance(img, bytes):
                # 压缩图片到 200KB 以内
                compressed_img = compress_image(img, max_size_kb=200)
                # 图片数据，转为 base64 data URL
                base64_data = self._encode_image_to_base64(compressed_img)
                image_url = f"data:image/png;base64,{base64_data}"
            else:
                # 已经是 URL
                image_url = img

            content.append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })

        return content

    @retry_on_429(max_retries=3, base_delay=2)
    def generate_text(
        self,
        prompt: str,
        model: str = "gemini-3-pro-preview",
        temperature: float = 1.0,
        max_output_tokens: int = 65535,
        images: List[Union[bytes, str]] = None,
        system_prompt: str = None,
        **kwargs
    ) -> str:
        """
        生成文本（支持图片输入）

        Args:
            prompt: 提示词
            model: 模型名称
            temperature: 温度
            max_output_tokens: 最大输出 token
            images: 图片列表（可选）
            system_prompt: 系统提示词（可选）

        Returns:
            生成的文本
        """
        messages = []

        # 添加系统提示词
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        # 构建用户消息内容
        content = self._build_content_with_images(prompt, images)
        messages.append({
            "role": "user",
            "content": content
        })

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_output_tokens,
            "stream": False
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        response = requests.post(
            self.chat_endpoint,
            json=payload,
            headers=headers,
            timeout=300  # 5分钟超时
        )

        if response.status_code != 200:
            error_detail = response.text[:500]
            raise Exception(
                f"Text API 请求失败 (状态码: {response.status_code})\n"
                f"错误详情: {error_detail}\n"
                f"请求地址: {self.chat_endpoint}\n"
                f"模型: {model}\n"
                "可能原因：\n"
                "1. API密钥无效或已过期\n"
                "2. 模型名称不正确或无权访问\n"
                "3. 请求超时或网络问题\n"
                "4. API配额已用尽\n"
                "5. Base URL配置错误\n"
                "建议：检查 TEXT_API_KEY 和 TEXT_API_BASE_URL 配置"
            )

        result = response.json()

        # 提取生成的文本
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            raise Exception(
                f"Text API 响应格式异常：未找到生成的文本。\n"
                f"响应数据: {str(result)[:500]}\n"
                "可能原因：\n"
                "1. API返回格式与OpenAI标准不一致\n"
                "2. 请求被拒绝或过滤\n"
                "3. 模型输出为空\n"
                "建议：检查API文档确认响应格式"
            )


# 全局客户端实例
_client_instance = None


def get_text_chat_client() -> TextChatClient:
    """获取全局 Text Chat 客户端实例"""
    global _client_instance
    if _client_instance is None:
        _client_instance = TextChatClient()
    return _client_instance


# 保留向后兼容的别名
def get_bltcy_chat_client() -> TextChatClient:
    """向后兼容的别名"""
    return get_text_chat_client()
