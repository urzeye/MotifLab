"""图片客户端模块（按需加载）。"""

from .base import BaseImageClient

__all__ = [
    "BaseImageClient",
    "OpenAICompatibleImageClient",
    "GoogleGenAIImageClient",
    "ImageApiClient",
    "get_image_client",
]


def __getattr__(name: str):
    """延迟导出客户端类，降低启动时可选依赖耦合。"""
    if name == "OpenAICompatibleImageClient":
        from .openai_compatible import OpenAICompatibleGenerator as OpenAICompatibleImageClient

        return OpenAICompatibleImageClient
    if name == "GoogleGenAIImageClient":
        from .google_genai import GoogleGenAIGenerator as GoogleGenAIImageClient

        return GoogleGenAIImageClient
    if name == "ImageApiClient":
        from .image_api import ImageApiGenerator as ImageApiClient

        return ImageApiClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def get_image_client(provider_config):
    provider_type = provider_config.get("type", "google_genai")
    if provider_type == "google_genai":
        from .google_genai import GoogleGenAIGenerator as GoogleGenAIImageClient

        return GoogleGenAIImageClient(provider_config)
    if provider_type == "image_api":
        from .image_api import ImageApiGenerator as ImageApiClient

        return ImageApiClient(provider_config)

    from .openai_compatible import OpenAICompatibleGenerator as OpenAICompatibleImageClient

    return OpenAICompatibleImageClient(provider_config)
