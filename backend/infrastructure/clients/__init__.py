"""统一客户端模块。"""

from .factory import ClientFactory
from .text import BaseTextClient, get_text_client
from .image import BaseImageClient, get_image_client

__all__ = [
    "ClientFactory",
    "BaseTextClient",
    "OpenAICompatibleTextClient",
    "GoogleGenAITextClient",
    "get_text_client",
    "BaseImageClient",
    "OpenAICompatibleImageClient",
    "GoogleGenAIImageClient",
    "ImageApiClient",
    "get_image_client",
]


def __getattr__(name: str):
    """延迟导出可选依赖相关客户端类。"""
    if name in {"OpenAICompatibleTextClient", "GoogleGenAITextClient"}:
        from . import text as text_module

        return getattr(text_module, name)
    if name in {"OpenAICompatibleImageClient", "GoogleGenAIImageClient", "ImageApiClient"}:
        from . import image as image_module

        return getattr(image_module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
