"""Text client module"""
from .base import BaseTextClient
from .openai_compatible import OpenAICompatibleTextClient
from .google_genai import GoogleGenAITextClient

__all__ = ['BaseTextClient', 'OpenAICompatibleTextClient', 'GoogleGenAITextClient']


def get_text_client(provider_config):
    provider_type = provider_config.get('type', 'openai_compatible')
    if provider_type == 'google_gemini':
        return GoogleGenAITextClient(provider_config)
    return OpenAICompatibleTextClient(provider_config)
