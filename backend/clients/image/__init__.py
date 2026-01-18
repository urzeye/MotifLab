"""Image client module"""
from .base import BaseImageClient
from .openai_compatible import OpenAICompatibleGenerator as OpenAICompatibleImageClient
from .google_genai import GoogleGenAIGenerator as GoogleGenAIImageClient
from .image_api import ImageApiGenerator as ImageApiClient

__all__ = [
    'BaseImageClient',
    'OpenAICompatibleImageClient', 
    'GoogleGenAIImageClient',
    'ImageApiClient'
]


def get_image_client(provider_config):
    provider_type = provider_config.get('type', 'google_genai')
    if provider_type == 'google_genai':
        return GoogleGenAIImageClient(provider_config)
    elif provider_type == 'image_api':
        return ImageApiClient(provider_config)
    else:
        return OpenAICompatibleImageClient(provider_config)
