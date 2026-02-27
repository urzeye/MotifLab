import os
import time
import threading
import logging
from http import HTTPStatus
from typing import Any, Dict, List, Optional

import requests
import dashscope
from dashscope import Generation, MultiModalConversation

from .base import ImageGeneratorBase

logger = logging.getLogger(__name__)
_DASHSCOPE_BASE_URL_LOCK = threading.Lock()

class DashScopeSdkGenerator(ImageGeneratorBase):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model = config.get('model') or 'qwen-image-max'
        self.size = config.get('size') or '1104*1472'
        self.negative_prompt = config.get('negative_prompt')
        self.prompt_extend = config.get('prompt_extend', True)
        self.watermark = config.get('watermark', False)
        self.n = config.get('n', 1)
        self.max_retries = int(config.get('max_retries', 2))
        # 文本压缩模型配置
        self.text_model = config.get('text_model', 'qwen3-max')

        # Client-side rate limit to avoid Throttling.RateQuota
        # Config overrides:
        # - rate_limit_rpm: requests per minute
        # - rate_limit_rps: requests per second
        # Default: qwen-image-max is 2 rpm; others 2 rps
        self.rate_limit_rpm = config.get('rate_limit_rpm')
        self.rate_limit_rps = config.get('rate_limit_rps')

        # Use a lock to coordinate across threads if caller uses concurrency.
        self._rate_lock = threading.Lock()
        self._next_allowed_ts = 0.0

        if self.api_key:
            dashscope.api_key = self.api_key
        elif os.getenv('DASHSCOPE_API_KEY'):
            dashscope.api_key = os.getenv('DASHSCOPE_API_KEY')

    def validate_config(self) -> bool:
        if not (self.api_key or os.getenv('DASHSCOPE_API_KEY') or getattr(dashscope, 'api_key', None)):
            raise ValueError(
                "DashScope API Key 未配置。\n"
                "解决方案：在系统设置页面填写 API Key，或设置环境变量 DASHSCOPE_API_KEY"
            )
        return True

    def _compress_prompt_if_needed(self, prompt: str, max_len: int) -> str:
        """
        如果 prompt 超过 500 字，使用文本模型压缩到 400-500 字
        """
        def _truncate(text: str) -> str:
            if len(text) <= max_len:
                return text
            if max_len <= 3:
                return text[:max_len]
            return text[:max_len - 3] + "..."

        if len(prompt) <= max_len:
            return prompt

        logger.info(f"Prompt 长度 {len(prompt)} 超过限制({max_len})，正在压缩...")

        # 使用文本模型压缩 prompt
        compression_prompt = f"""请将以下图片生成提示词精简到 {max_len} 字以内，保留所有关键视觉信息和要求：
原始提示词：
{prompt}

要求：
1. 保留核心画面描述、小红书风格、3:4比例、无Logo要求。
2. 保持指令的完整性。
3. 压缩后的文本必须控制在 {max_len} 字以内，严禁超出。
4. 直接输出压缩后的纯文本。"""

        try:
            normalized_base_url = self._normalize_base_url(self.base_url) if self.base_url else ''
            with _DASHSCOPE_BASE_URL_LOCK:
                old_base_url = getattr(dashscope, 'base_http_api_url', None)
                if normalized_base_url:
                    dashscope.base_http_api_url = normalized_base_url
                try:
                    response = Generation.call(
                        model=self.text_model,
                        prompt=compression_prompt,
                        result_format='message',
                        max_tokens=800
                    )
                finally:
                    if normalized_base_url:
                        dashscope.base_http_api_url = old_base_url

            if response.status_code == HTTPStatus.OK:
                compressed = response.output.choices[0].message.content.strip()
                logger.info(f"Prompt 压缩完成: {len(prompt)} -> {len(compressed)} 字符")
                # 强制截断作为最终兜底
                if len(compressed) > max_len:
                    logger.warning(f"压缩后长度仍然超标 ({len(compressed)})，执行强制截断至 {max_len}")
                return _truncate(compressed)
            else:
                logger.error(f"文本压缩 API 返回错误: {response.code} - {response.message}")
                return _truncate(prompt)
        except Exception as e:
            logger.error(f"Prompt 压缩异常: {str(e)}")
            return _truncate(prompt)

    def _save_temp_image(self, image_bytes: bytes) -> str:
        """将图片保存到临时文件并返回路径，避免使用 base64 导致 content 过长"""
        import tempfile
        # 使用系统的临时目录，或者项目内的临时目录
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "temp")
        os.makedirs(temp_dir, exist_ok=True)

        with tempfile.NamedTemporaryFile(suffix=".png", dir=temp_dir, delete=False) as tf:
            tf.write(image_bytes)
            return tf.name

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        url = (base_url or '').strip().rstrip('/')
        if not url:
            return ''
        marker = '/api/v1'
        idx = url.find(marker)
        if idx != -1:
            return url[:idx + len(marker)]
        if url.endswith('/api'):
            return url + '/v1'
        return url + '/api/v1'

    @staticmethod
    def _normalize_size(size: Optional[str]) -> str:
        allowed = {
            '1664*928',
            '1472*1104',
            '1328*1328',
            '1104*1472',
            '928*1664',
        }
        default_size = '1104*1472'
        raw = (size or '').strip()
        if not raw:
            return default_size
        normalized = raw.replace('x', '*').replace('X', '*')
        if normalized in allowed:
            return normalized
        mapping = {
            '1024*1024': '1328*1328',
            '768*768': '1328*1328',
        }
        fixed = mapping.get(normalized, default_size)
        logger.warning(f"DashScope size 参数不受支持: {raw}，已自动修正为 {fixed}")
        return fixed

    def generate_image(
        self,
        prompt: str,
        reference_image: Optional[bytes] = None,
        reference_images: Optional[List[bytes]] = None,
        model: Optional[str] = None,
        size: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        prompt_extend: Optional[bool] = None,
        watermark: Optional[bool] = None,
        n: Optional[int] = None,
        **kwargs,
    ) -> bytes:
        self.validate_config()

        final_model = model or self.model
        final_size = self._normalize_size(size or self.size)
        final_negative = negative_prompt if negative_prompt is not None else self.negative_prompt
        final_prompt_extend = self.prompt_extend if prompt_extend is None else prompt_extend
        final_watermark = self.watermark if watermark is None else watermark
        final_n = self.n if n is None else n

        # 目前 qwen-image-max 固定只支持 1 张
        if final_n != 1:
            logger.warning(f"DashScope qwen-image-max 目前仅支持 n=1，已自动修正: {final_n} -> 1")
            final_n = 1

        if final_negative and len(final_negative) > 500:
            logger.warning(f"negative_prompt 长度 {len(final_negative)} 超过限制，已自动截断至 500")
            final_negative = final_negative[:497] + "..."

        # 文生图：正向提示词最大 800；若外部仍传了参考图（本模型不使用），则进一步压缩到 200 兜底
        prompt_limit = 800
        if reference_image is not None or (reference_images is not None and len(reference_images) > 0):
            prompt_limit = 200

        final_prompt = prompt
        if len(final_prompt) > prompt_limit:
            final_prompt = self._compress_prompt_if_needed(final_prompt, prompt_limit)

        messages = [
            {
                "role": "user",
                "content": [{"text": final_prompt}],
            }
        ]

        call_kwargs: Dict[str, Any] = {
            'api_key': self.api_key or os.getenv('DASHSCOPE_API_KEY'),
            'model': final_model,
            'messages': messages,
            'result_format': 'message',
            'stream': False,
            'watermark': final_watermark,
            'prompt_extend': final_prompt_extend,
            'size': final_size,
            'n': final_n,
        }

        if final_negative:
            call_kwargs['negative_prompt'] = final_negative

        normalized_base_url = self._normalize_base_url(self.base_url) if self.base_url else ''

        attempt = 0
        while True:
            self._apply_rate_limit(final_model)

            with _DASHSCOPE_BASE_URL_LOCK:
                old_base_url = getattr(dashscope, 'base_http_api_url', None)
                if normalized_base_url:
                    dashscope.base_http_api_url = normalized_base_url
                try:
                    response = MultiModalConversation.call(**call_kwargs)
                finally:
                    if normalized_base_url:
                        dashscope.base_http_api_url = old_base_url

            if response.status_code == HTTPStatus.OK:
                break

            code = getattr(response, 'code', '')
            message = getattr(response, 'message', '')
            if response.status_code == 429 and code == 'Throttling.RateQuota' and attempt < self.max_retries:
                sleep_s = min(60.0, (2 ** attempt) * 1.5)
                time.sleep(sleep_s)
                attempt += 1
                continue

            raise Exception(
                f"DashScope 请求失败 (状态码: {response.status_code})\n"
                f"错误码: {code}\n"
                f"错误信息: {message}\n"
                f"模型: {final_model}"
            )

        try:
            choices = response.output.choices
            if not choices or len(choices) == 0:
                raise ValueError('未在响应中找到 choices')
            content = choices[0].message.content

            image_url = None
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get('image'):
                        image_url = item.get('image')
                        break
            elif isinstance(content, dict):
                image_url = content.get('image')

            if not image_url:
                raise ValueError('未在响应中找到 image URL')
        except Exception as e:
            raise Exception(f"DashScope 响应解析失败: {str(e)}")

        img = requests.get(image_url, timeout=60)
        if img.status_code != 200:
            raise Exception(f"下载图片失败: HTTP {img.status_code}")
        return img.content

    def _apply_rate_limit(self, model: str) -> None:
        model_lower = (model or '').lower()

        rpm = self.rate_limit_rpm
        rps = self.rate_limit_rps

        if rpm is None and rps is None:
            if model_lower.startswith('qwen-image-max'):
                rpm = 2
            else:
                rps = 2

        if rpm is not None:
            min_interval = 60.0 / float(rpm)
        else:
            min_interval = 1.0 / float(rps or 1)

        with self._rate_lock:
            now = time.time()
            if now < self._next_allowed_ts:
                time.sleep(self._next_allowed_ts - now)
            self._next_allowed_ts = max(now, self._next_allowed_ts) + min_interval

    @staticmethod
    def _to_data_url(image_bytes: bytes) -> str:
        import base64

        b64 = base64.b64encode(image_bytes).decode('utf-8')
        return f"data:image/png;base64,{b64}"
