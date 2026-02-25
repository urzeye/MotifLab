import os
import time
import threading
from http import HTTPStatus
from typing import Any, Dict, List, Optional

import requests
import dashscope
from dashscope import MultiModalConversation

from .base import ImageGeneratorBase


class DashScopeSdkGenerator(ImageGeneratorBase):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model = config.get('model') or 'qwen-image-max'
        self.size = config.get('size') or '1024*1024'
        self.negative_prompt = config.get('negative_prompt')
        self.prompt_extend = config.get('prompt_extend', True)
        self.watermark = config.get('watermark', False)
        self.n = config.get('n', 1)
        self.max_retries = int(config.get('max_retries', 2))

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

        if config.get('base_url'):
            dashscope.base_http_api_url = config['base_url']

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
        final_size = size or self.size
        final_negative = negative_prompt if negative_prompt is not None else self.negative_prompt
        final_prompt_extend = self.prompt_extend if prompt_extend is None else prompt_extend
        final_watermark = self.watermark if watermark is None else watermark
        final_n = self.n if n is None else n

        all_refs: List[bytes] = []
        if reference_images:
            all_refs.extend(reference_images)
        if reference_image and reference_image not in all_refs:
            all_refs.append(reference_image)

        content: List[Dict[str, Any]] = []
        if all_refs:
            ref = all_refs[0]
            content.append({"image": self._to_data_url(ref)})
        content.append({"text": prompt})

        messages = [{"role": "user", "content": content}]

        call_kwargs: Dict[str, Any] = {
            'api_key': self.api_key or os.getenv('DASHSCOPE_API_KEY'),
            'model': final_model,
            'messages': messages,
            'result_format': 'message',
            'stream': False,
            'watermark': final_watermark,
            'prompt_extend': final_prompt_extend,
        }

        if final_negative:
            call_kwargs['negative_prompt'] = final_negative

        if final_n is not None:
            call_kwargs['n'] = final_n

        if final_size and (final_n in [None, 1]):
            call_kwargs['size'] = final_size

        attempt = 0
        while True:
            self._apply_rate_limit(final_model)
            response = MultiModalConversation.call(**call_kwargs)

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
            contents = response.output.choices[0].message.content
            image_url = None
            for item in contents:
                if isinstance(item, dict) and item.get('image'):
                    image_url = item['image']
                    break
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
