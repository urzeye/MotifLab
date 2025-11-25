"""OpenAI 兼容接口图片生成器"""
import time
import random
import base64
from functools import wraps
from typing import Dict, Any
import requests
from .base import ImageGeneratorBase


def retry_on_error(max_retries=5, base_delay=3):
    """错误自动重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e)
                    # 检查是否是速率限制错误
                    if "429" in error_str or "rate" in error_str.lower():
                        if attempt < max_retries - 1:
                            wait_time = (base_delay ** attempt) + random.uniform(0, 1)
                            print(f"[重试] 遇到速率限制，{wait_time:.1f}秒后重试 (尝试 {attempt + 2}/{max_retries})")
                            time.sleep(wait_time)
                            continue
                    # 其他错误或重试耗尽
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        print(f"[重试] 请求失败: {error_str[:100]}，{wait_time}秒后重试")
                        time.sleep(wait_time)
                        continue
                    raise
            raise Exception(f"重试 {max_retries} 次后仍失败")
        return wrapper
    return decorator


class OpenAICompatibleGenerator(ImageGeneratorBase):
    """OpenAI 兼容接口图片生成器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        if not self.api_key:
            raise ValueError("API Key 未配置")

        if not self.base_url:
            raise ValueError("Base URL 未配置")

        # 默认模型
        self.default_model = config.get('model', 'dall-e-3')

        # API 端点类型: 'images' 或 'chat'
        self.endpoint_type = config.get('endpoint_type', 'images')

    def validate_config(self) -> bool:
        """验证配置"""
        return bool(self.api_key and self.base_url)

    @retry_on_error(max_retries=5, base_delay=3)
    def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        model: str = None,
        quality: str = "standard",
        **kwargs
    ) -> bytes:
        """
        生成图片

        Args:
            prompt: 提示词
            size: 图片尺寸 (如 "1024x1024", "2048x2048", "4096x4096")
            model: 模型名称
            quality: 质量 ("standard" 或 "hd")
            **kwargs: 其他参数

        Returns:
            图片二进制数据
        """
        if model is None:
            model = self.default_model

        if self.endpoint_type == 'images':
            return self._generate_via_images_api(prompt, size, model, quality)
        elif self.endpoint_type == 'chat':
            return self._generate_via_chat_api(prompt, size, model)
        else:
            raise ValueError(f"不支持的端点类型: {self.endpoint_type}")

    def _generate_via_images_api(
        self,
        prompt: str,
        size: str,
        model: str,
        quality: str
    ) -> bytes:
        """通过 /v1/images/generations 端点生成"""
        url = f"{self.base_url.rstrip('/')}/v1/images/generations"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "response_format": "b64_json"  # 使用base64格式更可靠
        }

        # 如果模型支持quality参数
        if quality and model.startswith('dall-e'):
            payload["quality"] = quality

        response = requests.post(url, headers=headers, json=payload, timeout=180)

        if response.status_code != 200:
            raise Exception(f"API请求失败: {response.status_code} - {response.text}")

        result = response.json()

        if "data" not in result or len(result["data"]) == 0:
            raise ValueError("API未返回图片数据")

        image_data = result["data"][0]

        # 处理base64格式
        if "b64_json" in image_data:
            return base64.b64decode(image_data["b64_json"])

        # 处理URL格式
        elif "url" in image_data:
            img_response = requests.get(image_data["url"], timeout=60)
            if img_response.status_code == 200:
                return img_response.content
            else:
                raise Exception(f"下载图片失败: {img_response.status_code}")

        else:
            raise ValueError("未找到图片数据")

    def _generate_via_chat_api(
        self,
        prompt: str,
        size: str,
        model: str
    ) -> bytes:
        """通过 /v1/chat/completions 端点生成（某些服务商使用此方式）"""
        url = f"{self.base_url.rstrip('/')}/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 4096,
            "temperature": 1.0,
            # 尝试添加图片相关参数
            "response_format": {"type": "image"},
            "size": size
        }

        response = requests.post(url, headers=headers, json=payload, timeout=180)

        if response.status_code != 200:
            raise Exception(f"API请求失败: {response.status_code} - {response.text}")

        result = response.json()

        # 这部分需要根据具体服务商的返回格式调整
        # 假设返回格式类似OpenAI
        if "choices" in result and len(result["choices"]) > 0:
            choice = result["choices"][0]
            # 需要根据实际返回格式解析图片数据
            # 这里是一个示例，实际需要调整
            if "message" in choice and "content" in choice["message"]:
                content = choice["message"]["content"]
                # 如果是base64
                if isinstance(content, str) and content.startswith("data:image"):
                    base64_data = content.split(",")[1]
                    return base64.b64decode(base64_data)

        raise ValueError("无法从chat API响应中提取图片数据")

    def get_supported_sizes(self) -> list:
        """获取支持的图片尺寸"""
        # 默认OpenAI支持的尺寸
        return self.config.get('supported_sizes', [
            "1024x1024",
            "1792x1024",
            "1024x1792",
            "2048x2048",
            "4096x4096"
        ])
