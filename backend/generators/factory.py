"""图片生成器工厂"""
from typing import Dict, Any
from .base import ImageGeneratorBase
from .google_genai import GoogleGenAIGenerator
from .openai_compatible import OpenAICompatibleGenerator
from .image_api import ImageApiGenerator


class ImageGeneratorFactory:
    """图片生成器工厂类"""

    # 注册的生成器类型
    GENERATORS = {
        'google_genai': GoogleGenAIGenerator,
        'openai': OpenAICompatibleGenerator,
        'openai_compatible': OpenAICompatibleGenerator,
        'image_api': ImageApiGenerator,
    }

    @classmethod
    def create(cls, provider: str, config: Dict[str, Any]) -> ImageGeneratorBase:
        """
        创建图片生成器实例

        Args:
            provider: 服务商类型 ('google_genai', 'openai', 'openai_compatible')
            config: 配置字典

        Returns:
            图片生成器实例

        Raises:
            ValueError: 不支持的服务商类型
        """
        if provider not in cls.GENERATORS:
            raise ValueError(
                f"不支持的服务商: {provider}. "
                f"支持的类型: {list(cls.GENERATORS.keys())}"
            )

        generator_class = cls.GENERATORS[provider]
        return generator_class(config)

    @classmethod
    def register_generator(cls, name: str, generator_class: type):
        """
        注册自定义生成器

        Args:
            name: 生成器名称
            generator_class: 生成器类
        """
        if not issubclass(generator_class, ImageGeneratorBase):
            raise TypeError("生成器必须继承自 ImageGeneratorBase")

        cls.GENERATORS[name] = generator_class
