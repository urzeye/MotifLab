"""图片生成器工厂。"""

from __future__ import annotations

import importlib
from typing import Any, Dict, Tuple

from .base import ImageGeneratorBase


class ImageGeneratorFactory:
    """图片生成器工厂类"""

    # 生成器注册表：provider -> (模块路径, 类名)
    GENERATORS: Dict[str, Tuple[str, str]] = {
        "openai_compatible": ("backend.generators.openai_compatible", "OpenAICompatibleGenerator"),
        "openai": ("backend.generators.openai_compatible", "OpenAICompatibleGenerator"),
        "google_genai": ("backend.generators.google_genai", "GoogleGenAIGenerator"),
        "image_api": ("backend.generators.image_api", "ImageApiGenerator"),
        "dashscope": ("backend.generators.dashscope_sdk", "DashScopeSdkGenerator"),
        "dashscope_edit": ("backend.generators.dashscope_edit", "DashScopeImageEditGenerator"),
        "modelscope": ("backend.generators.modelscope", "ModelScopeGenerator"),
        "replicate": ("backend.generators.replicate_gen", "ReplicateGenerator"),
    }

    # 已加载的生成器类缓存，避免重复 import
    _GENERATOR_CLASS_CACHE: Dict[str, type] = {}

    @classmethod
    def _load_generator_class(cls, provider: str) -> type:
        """按需加载生成器类。"""
        if provider in cls._GENERATOR_CLASS_CACHE:
            return cls._GENERATOR_CLASS_CACHE[provider]

        module_path, class_name = cls.GENERATORS[provider]
        try:
            module = importlib.import_module(module_path)
            generator_class = getattr(module, class_name)
        except Exception as exc:
            raise ImportError(f"加载图片生成器失败: provider={provider}, error={exc}") from exc

        if not issubclass(generator_class, ImageGeneratorBase):
            raise TypeError(
                f"加载失败：{class_name} 必须继承自 ImageGeneratorBase，"
                f"当前类型: {generator_class}"
            )

        cls._GENERATOR_CLASS_CACHE[provider] = generator_class
        return generator_class

    @classmethod
    def create(cls, provider: str, config: Dict[str, Any]) -> ImageGeneratorBase:
        """
        创建图片生成器实例

        参数:
            provider: 服务商类型（如 google_genai、openai、openai_compatible）
            config: 配置字典

        返回:
            图片生成器实例

        异常:
            ValueError: 不支持的服务商类型
        """
        if provider not in cls.GENERATORS:
            available = ', '.join(cls.GENERATORS.keys())
            raise ValueError(
                f"不支持的图片生成服务商: {provider}\n"
                f"支持的服务商类型: {available}\n"
                "解决方案：\n"
                "1. 检查系统设置中的图片服务商 active_provider 配置\n"
                "2. 确认 provider.type 字段是否正确\n"
                "3. 或使用环境变量 IMAGE_PROVIDER 指定服务商"
            )

        generator_class = cls._load_generator_class(provider)
        return generator_class(config)

    @classmethod
    def register_generator(cls, name: str, generator_class: type):
        """
        注册自定义生成器

        参数:
            name: 生成器名称
            generator_class: 生成器类
        """
        if not issubclass(generator_class, ImageGeneratorBase):
            raise TypeError(
                f"注册失败：生成器类必须继承自 ImageGeneratorBase。\n"
                f"提供的类: {generator_class.__name__}\n"
                f"基类: ImageGeneratorBase"
            )

        cls.GENERATORS[name] = (generator_class.__module__, generator_class.__name__)
        cls._GENERATOR_CLASS_CACHE[name] = generator_class
