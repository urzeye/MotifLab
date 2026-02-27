"""DashScope 图像编辑生成器 - 支持风格迁移和多图融合"""
import os
import base64
import time
import threading
import logging
import mimetypes
from http import HTTPStatus
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, unquote
from pathlib import PurePosixPath

import requests
import dashscope
from dashscope import ImageSynthesis

from .base import ImageGeneratorBase

logger = logging.getLogger(__name__)
_DASHSCOPE_BASE_URL_LOCK = threading.Lock()


class DashScopeImageEditGenerator(ImageGeneratorBase):
    """
    DashScope 图像编辑生成器

    支持模型：
    - wan2.5-i2i-preview: 通义万相2.5图像编辑，支持多图融合、风格迁移、主体特征保持
    - qwen-image-edit-plus: 通义千问图像编辑，支持单图编辑和多图融合

    核心能力：
    - 风格迁移：将参考图的视觉风格迁移到新生成的图片
    - 多图融合：融合多张图片的元素
    - 主体特征保持：保持人物/物体的一致性
    """

    # 支持的尺寸映射（宽高比 -> 像素尺寸）
    SIZE_MAPPING = {
        '1:1': '1280*1280',
        '2:3': '800*1200',
        '3:2': '1200*800',
        '3:4': '960*1280',
        '4:3': '1280*960',
        '9:16': '720*1280',
        '16:9': '1280*720',
        '21:9': '1344*576',
    }

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model = config.get('model') or 'wan2.5-i2i-preview'
        self.size = config.get('size') or '1280*1280'
        self.negative_prompt = config.get('negative_prompt')
        self.prompt_extend = config.get('prompt_extend', True)
        self.watermark = config.get('watermark', False)
        self.n = config.get('n', 1)
        self.max_retries = int(config.get('max_retries', 2))
        self.seed = config.get('seed')

        # 速率限制配置
        self.rate_limit_rpm = config.get('rate_limit_rpm', 2)
        self._rate_lock = threading.Lock()
        self._next_allowed_ts = 0.0

        if self.api_key:
            dashscope.api_key = self.api_key
        elif os.getenv('DASHSCOPE_API_KEY'):
            dashscope.api_key = os.getenv('DASHSCOPE_API_KEY')

        logger.info(f"DashScopeImageEditGenerator 初始化完成: model={self.model}")

    def validate_config(self) -> bool:
        if not (self.api_key or os.getenv('DASHSCOPE_API_KEY') or getattr(dashscope, 'api_key', None)):
            raise ValueError(
                "DashScope API Key 未配置。\n"
                "解决方案：在系统设置页面填写 API Key，或设置环境变量 DASHSCOPE_API_KEY"
            )
        return True

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        """规范化 base_url"""
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
    def _encode_image_to_base64(image_bytes: bytes, mime_type: str = 'image/png') -> str:
        """将图片字节转换为 Base64 Data URL 格式"""
        b64 = base64.b64encode(image_bytes).decode('utf-8')
        return f"data:{mime_type};base64,{b64}"

    def _aspect_ratio_to_size(self, aspect_ratio: str) -> str:
        """将宽高比转换为像素尺寸"""
        return self.SIZE_MAPPING.get(aspect_ratio, self.size)

    def _apply_rate_limit(self) -> None:
        """应用速率限制"""
        min_interval = 60.0 / float(self.rate_limit_rpm or 2)

        with self._rate_lock:
            now = time.time()
            if now < self._next_allowed_ts:
                sleep_time = self._next_allowed_ts - now
                logger.debug(f"速率限制：等待 {sleep_time:.2f} 秒")
                time.sleep(sleep_time)
            self._next_allowed_ts = max(now, self._next_allowed_ts) + min_interval

    def generate_image(
        self,
        prompt: str,
        reference_image: Optional[bytes] = None,
        reference_images: Optional[List[bytes]] = None,
        model: Optional[str] = None,
        size: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        prompt_extend: Optional[bool] = None,
        watermark: Optional[bool] = None,
        n: Optional[int] = None,
        seed: Optional[int] = None,
        style_transfer: bool = True,
        **kwargs,
    ) -> bytes:
        """
        生成图片（基于参考图进行风格迁移或图像编辑）

        Args:
            prompt: 生成提示词
            reference_image: 单张参考图片（风格参考）
            reference_images: 多张参考图片列表
            model: 模型名称 (wan2.5-i2i-preview / qwen-image-edit-plus)
            size: 输出尺寸 (如 "960*1280")
            aspect_ratio: 宽高比 (如 "3:4")，会自动转换为 size
            negative_prompt: 反向提示词
            prompt_extend: 是否启用提示词扩展
            watermark: 是否添加水印
            n: 生成数量 (1-4)
            seed: 随机种子
            style_transfer: 是否启用风格迁移模式（自动增强提示词）

        Returns:
            生成的图片二进制数据
        """
        self.validate_config()

        final_model = model or self.model
        final_negative = negative_prompt if negative_prompt is not None else self.negative_prompt
        final_prompt_extend = self.prompt_extend if prompt_extend is None else prompt_extend
        final_watermark = self.watermark if watermark is None else watermark
        final_n = min(self.n if n is None else n, 4)
        final_seed = seed if seed is not None else self.seed

        # 处理尺寸：优先使用 aspect_ratio 转换
        if aspect_ratio:
            final_size = self._aspect_ratio_to_size(aspect_ratio)
        else:
            final_size = size or self.size

        logger.info(f"DashScope 图像编辑: model={final_model}, size={final_size}")

        # 构建图片列表
        images = []

        # 处理参考图片
        if reference_images:
            for i, img_bytes in enumerate(reference_images[:3]):
                img_b64 = self._encode_image_to_base64(img_bytes)
                images.append(img_b64)
                logger.debug(f"添加参考图 {i+1}: {len(img_bytes)} bytes")
        elif reference_image:
            img_b64 = self._encode_image_to_base64(reference_image)
            images.append(img_b64)
            logger.debug(f"添加参考图: {len(reference_image)} bytes")

        if not images:
            raise ValueError(
                "❌ 图像编辑模式需要至少一张参考图片\n\n"
                "【说明】\n"
                "DashScope 图像编辑模型需要输入参考图片才能工作。\n\n"
                "【解决方案】\n"
                "1. 如果是首张图片，请使用文生图模式 (dashscope)\n"
                "2. 后续图片使用图像编辑模式 (dashscope_edit) 并传入第一张图作为参考"
            )

        # 构建提示词
        if style_transfer and len(images) == 1:
            # 风格迁移提示词：保持视觉风格，但生成全新的画面内容
            # 重点：避免只是填充文字，而是要生成新的视觉场景
            enhanced_prompt = (
                f"【核心任务】参考[图1]的视觉风格，创作一张全新的图片。\n\n"
                f"【风格参考 - 从图1中提取】\n"
                f"- 色彩风格：使用与[图1]相似的色调和配色方案\n"
                f"- 设计语言：保持与[图1]一致的设计美学\n"
                f"- 氛围基调：延续[图1]的整体氛围和情绪\n\n"
                f"【新图片内容 - 最高优先级】\n{prompt}\n\n"
                f"【重要说明】\n"
                f"- 这是一张全新的图片，不是在[图1]上添加文字\n"
                f"- 需要根据新内容创作新的视觉场景和画面\n"
                f"- 文字内容要融入新的画面设计中，而不是简单叠加\n"
                f"- 保持风格统一，但画面构图可以完全不同"
            )
            # 风格迁移模式下，关闭 prompt_extend 以避免模型自动扩展覆盖风格要求
            final_prompt_extend = False
        else:
            enhanced_prompt = prompt

        logger.debug(f"最终提示词长度: {len(enhanced_prompt)} 字符")

        # 构建调用参数
        call_kwargs: Dict[str, Any] = {
            'api_key': self.api_key or os.getenv('DASHSCOPE_API_KEY'),
            'model': final_model,
            'prompt': enhanced_prompt,
            'images': images,
            'n': final_n,
            'prompt_extend': final_prompt_extend,
            'watermark': final_watermark,
        }

        if final_size:
            call_kwargs['size'] = final_size
        if final_negative:
            call_kwargs['negative_prompt'] = final_negative
        if final_seed is not None:
            call_kwargs['seed'] = final_seed

        normalized_base_url = self._normalize_base_url(self.base_url) if self.base_url else ''

        # 重试逻辑
        attempt = 0
        while True:
            self._apply_rate_limit()

            with _DASHSCOPE_BASE_URL_LOCK:
                old_base_url = getattr(dashscope, 'base_http_api_url', None)
                if normalized_base_url:
                    dashscope.base_http_api_url = normalized_base_url
                try:
                    logger.debug(f"调用 ImageSynthesis.call: attempt={attempt}")
                    response = ImageSynthesis.call(**call_kwargs)
                finally:
                    if normalized_base_url:
                        dashscope.base_http_api_url = old_base_url

            if response.status_code == HTTPStatus.OK:
                break

            code = getattr(response, 'code', '')
            message = getattr(response, 'message', '')

            # 速率限制重试
            if response.status_code == 429 and code == 'Throttling.RateQuota' and attempt < self.max_retries:
                sleep_s = min(60.0, (2 ** attempt) * 2.0)
                logger.warning(f"速率限制，等待 {sleep_s} 秒后重试...")
                time.sleep(sleep_s)
                attempt += 1
                continue

            # 解析错误信息
            error_msg = self._parse_error(response.status_code, code, message, final_model)
            raise Exception(error_msg)

        # 解析响应
        try:
            results = response.output.results
            if not results:
                raise ValueError('响应中未找到生成结果')

            image_url = results[0].url
            if not image_url:
                raise ValueError('响应中未找到图片 URL')

            logger.debug(f"获取图片 URL: {image_url[:100]}...")

        except Exception as e:
            raise Exception(f"DashScope 响应解析失败: {str(e)}")

        # 下载图片
        img_response = requests.get(image_url, timeout=60)
        if img_response.status_code != 200:
            raise Exception(f"下载图片失败: HTTP {img_response.status_code}")

        logger.info(f"✅ DashScope 图像编辑成功: {len(img_response.content)} bytes")
        return img_response.content

    def _parse_error(self, status_code: int, code: str, message: str, model: str) -> str:
        """解析错误信息，返回用户友好的提示"""
        code_lower = (code or '').lower()
        message_lower = (message or '').lower()

        if status_code == 401 or 'unauthorized' in code_lower:
            return (
                "❌ API Key 认证失败\n\n"
                "【解决方案】\n"
                "1. 检查 API Key 是否正确\n"
                "2. 前往阿里云百炼控制台获取 API Key"
            )

        if status_code == 429 or 'throttling' in code_lower:
            return (
                "⏳ 请求频率超限\n\n"
                "【解决方案】\n"
                "1. 稍等片刻后重试\n"
                "2. 减少并发请求数量"
            )

        if 'invalid' in code_lower and 'image' in message_lower:
            return (
                "❌ 图片格式或尺寸不符合要求\n\n"
                "【要求】\n"
                "- 格式：JPEG、PNG、BMP、WEBP\n"
                "- 分辨率：384-5000 像素\n"
                "- 大小：不超过 10MB"
            )

        if 'content' in code_lower or 'safety' in message_lower:
            return (
                "🛡️ 内容被安全过滤器拦截\n\n"
                "【解决方案】\n"
                "1. 修改提示词，避免敏感内容\n"
                "2. 使用更中性的描述"
            )

        return (
            f"❌ DashScope 请求失败\n\n"
            f"【错误信息】\n"
            f"状态码: {status_code}\n"
            f"错误码: {code}\n"
            f"详情: {message}\n"
            f"模型: {model}"
        )

    def get_supported_aspect_ratios(self) -> list:
        """获取支持的宽高比"""
        return list(self.SIZE_MAPPING.keys())

    def get_supported_sizes(self) -> list:
        """获取支持的尺寸"""
        return list(self.SIZE_MAPPING.values())
