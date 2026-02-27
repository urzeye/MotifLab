"""Replicate 图片生成器。"""
import logging
from typing import Any, Dict, List, Tuple

import requests

from .base import ImageGeneratorBase

logger = logging.getLogger(__name__)

try:
    import replicate
except ImportError:
    replicate = None


class ReplicateGenerator(ImageGeneratorBase):
    """基于 Replicate API 的图片生成器。"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model = config.get('model') or (
            'prunaai/z-image-turbo:'
            '0870559624690b3709350177b9d521d84e54d297026d725358b8f73193429e91'
        )
        self.default_steps = int(config.get('steps', 9))
        self.default_guidance = float(config.get('guidance', 0.0))

    def validate_config(self) -> bool:
        if not self.api_key:
            raise ValueError("Replicate API Key 未配置")
        if replicate is None:
            raise ImportError("缺少 replicate 依赖，请先安装 replicate 包")
        return True

    def generate_image(self, prompt: str, aspect_ratio: str = "3:4", **kwargs) -> bytes:
        self.validate_config()

        width, height = self._get_dimensions(aspect_ratio)
        client = replicate.Client(api_token=self.api_key)

        input_params = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_inference_steps": kwargs.get('steps', self.default_steps),
            "guidance_scale": kwargs.get('guidance', self.default_guidance),
            "output_format": "png",
        }
        if 'seed' in kwargs:
            input_params['seed'] = kwargs['seed']

        logger.info(f"Replicate 生成图片: model={self.model}, ratio={aspect_ratio}, size={width}x{height}")

        output = client.run(self.model, input=input_params)
        image_url = output[0] if isinstance(output, list) else output
        return self._download_image(str(image_url))

    def _download_image(self, url: str) -> bytes:
        response = requests.get(url, timeout=60)
        if response.status_code != 200:
            raise RuntimeError(f"下载 Replicate 图片失败: HTTP {response.status_code}")
        return response.content

    def _get_dimensions(self, aspect_ratio: str) -> Tuple[int, int]:
        mapping = {
            "1:1": (1024, 1024),
            "3:4": (896, 1152),
            "4:3": (1152, 896),
            "9:16": (768, 1344),
            "16:9": (1344, 768),
        }
        return mapping.get(aspect_ratio, (896, 1152))

    def get_supported_aspect_ratios(self) -> List[str]:
        return ["1:1", "3:4", "4:3", "9:16", "16:9"]
