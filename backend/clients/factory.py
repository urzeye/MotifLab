"""统一客户端工厂。"""

from typing import Dict, Any, Union

from .text import BaseTextClient, get_text_client
from .image import BaseImageClient, get_image_client


class ClientFactory:
    # 仅保留可观察的 provider 映射，不在导入阶段加载具体实现类
    TEXT_CLIENTS = {
        "google_gemini": "backend.clients.text.google_genai.GoogleGenAITextClient",
        "openai": "backend.clients.text.openai_compatible.OpenAICompatibleTextClient",
        "openai_compatible": "backend.clients.text.openai_compatible.OpenAICompatibleTextClient",
    }

    @classmethod
    def create_text_client(cls, provider_config: Dict[str, Any]) -> BaseTextClient:
        return get_text_client(provider_config)

    @classmethod
    def create_image_client(cls, provider_config: Dict[str, Any]) -> BaseImageClient:
        return get_image_client(provider_config)

    @classmethod
    def create(cls, client_type: str, provider_config: Dict[str, Any]) -> Union[BaseTextClient, BaseImageClient]:
        if client_type == 'text':
            return cls.create_text_client(provider_config)
        elif client_type == 'image':
            return cls.create_image_client(provider_config)
        else:
            raise ValueError(f'Unknown client type: {client_type}')
