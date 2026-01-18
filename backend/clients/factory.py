"""Unified client factory for text and image clients"""
from typing import Dict, Any, Optional, Union
from .text import BaseTextClient, OpenAICompatibleTextClient, GoogleGenAITextClient, get_text_client
from .image import BaseImageClient, get_image_client


class ClientFactory:
    TEXT_CLIENTS = {
        'google_gemini': GoogleGenAITextClient,
        'openai': OpenAICompatibleTextClient,
        'openai_compatible': OpenAICompatibleTextClient,
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
