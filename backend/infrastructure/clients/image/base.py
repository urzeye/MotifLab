"""Base image client abstract class"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class BaseImageClient(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get('api_key')
        self.base_url = config.get('base_url')
        self.default_model = config.get('model')

    @abstractmethod
    def generate_image(self, prompt: str, **kwargs) -> bytes:
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        pass

    def get_supported_sizes(self) -> List[str]:
        return self.config.get('supported_sizes', ['1024x1024'])

    def get_supported_aspect_ratios(self) -> List[str]:
        return self.config.get('supported_aspect_ratios', ['1:1', '3:4', '16:9'])
