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
            raise Exception(f"重试 {max_retries} 次后仍失败")
        return wrapper
    return decorator


class TextChatClient:
    """Text API 客户端封装类"""

    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv("TEXT_API_KEY") or os.getenv("BLTCY_API_KEY")
        if not self.api_key:
            raise ValueError("TEXT_API_KEY 环境变量未设置")

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
            raise Exception(f"API 请求失败: {response.status_code} - {response.text}")

        result = response.json()

        # 提取生成的文本
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            raise Exception(f"API 响应格式异常: {result}")


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
