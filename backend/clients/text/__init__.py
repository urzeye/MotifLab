"""文本客户端模块（按需加载）。"""

from .base import BaseTextClient

__all__ = ["BaseTextClient", "OpenAICompatibleTextClient", "GoogleGenAITextClient", "get_text_client"]


def __getattr__(name: str):
    """延迟导出客户端类，避免可选依赖在导入阶段触发。"""
    if name == "OpenAICompatibleTextClient":
        from .openai_compatible import OpenAICompatibleTextClient

        return OpenAICompatibleTextClient
    if name == "GoogleGenAITextClient":
        from .google_genai import GoogleGenAITextClient

        return GoogleGenAITextClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def get_text_client(provider_config):
    provider_type = provider_config.get("type", "openai_compatible")
    if provider_type == "google_gemini":
        from .google_genai import GoogleGenAITextClient

        return GoogleGenAITextClient(provider_config)

    from .openai_compatible import OpenAICompatibleTextClient

    return OpenAICompatibleTextClient(provider_config)
