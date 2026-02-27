"""ModelScope Z-Image 图片生成器。"""
import logging
import time
from typing import Any, Dict, List

import requests

from .base import ImageGeneratorBase

logger = logging.getLogger(__name__)


class ModelScopeGenerator(ImageGeneratorBase):
    """ModelScope 异步任务图片生成器。"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = (config.get('base_url') or 'https://api-inference.modelscope.cn').rstrip('/')
        self.model = config.get('model') or 'Tongyi-MAI/Z-Image-Turbo'
        self.poll_interval = max(1, int(config.get('polling_interval', 2)))
        self.timeout_seconds = max(10, int(config.get('timeout', 120)))

    def validate_config(self) -> bool:
        if not self.api_key:
            raise ValueError("ModelScope API Key 未配置")
        return True

    def generate_image(self, prompt: str, **kwargs) -> bytes:
        """提交任务并轮询结果，返回图片二进制。"""
        self.validate_config()

        # ModelScope 对长 prompt 较敏感，做上限保护。
        max_prompt_length = 1800
        if len(prompt) > max_prompt_length:
            logger.warning(f"ModelScope prompt 过长 ({len(prompt)}), 截断到 {max_prompt_length}")
            prompt = prompt[:max_prompt_length]

        task_id = self._submit_task(prompt)
        image_url = self._poll_until_done(task_id)
        return self._download_image(image_url)

    def _submit_task(self, prompt: str) -> str:
        url = f"{self.base_url}/v1/images/generations"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-ModelScope-Async-Mode": "true",
        }
        payload = {
            "model": self.model,
            "prompt": prompt,
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code != 200:
            raise RuntimeError(f"ModelScope 提交任务失败: HTTP {response.status_code} {response.text[:200]}")

        data = response.json()
        task_id = data.get("task_id")
        if not task_id:
            raise RuntimeError(f"ModelScope 返回异常，缺少 task_id: {str(data)[:300]}")
        return task_id

    def _poll_until_done(self, task_id: str) -> str:
        url = f"{self.base_url}/v1/tasks/{task_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-ModelScope-Task-Type": "image_generation",
        }

        start = time.time()
        while True:
            if time.time() - start > self.timeout_seconds:
                raise TimeoutError(f"ModelScope 任务超时（>{self.timeout_seconds}s）: {task_id}")

            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code != 200:
                raise RuntimeError(f"ModelScope 查询任务失败: HTTP {response.status_code} {response.text[:200]}")

            data = response.json()
            status = (data.get("task_status") or "").upper()

            if status == "SUCCEED":
                output_images = data.get("output_images") or []
                if not output_images:
                    raise RuntimeError("ModelScope 任务成功但未返回图片地址")
                return output_images[0]

            if status == "FAILED":
                message = data.get("message") or "未知错误"
                raise RuntimeError(f"ModelScope 任务失败: {message}")

            time.sleep(self.poll_interval)

    def _download_image(self, url: str) -> bytes:
        response = requests.get(url, timeout=60)
        if response.status_code != 200:
            raise RuntimeError(f"下载 ModelScope 图片失败: HTTP {response.status_code}")
        return response.content

    def get_supported_sizes(self) -> List[str]:
        return ["1024x1024"]

    def get_supported_aspect_ratios(self) -> List[str]:
        return ["1:1", "3:4", "4:3", "9:16", "16:9"]
