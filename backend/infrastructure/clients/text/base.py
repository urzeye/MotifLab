"""Base text client abstract class"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union


class BaseTextClient(ABC):
    def __init__(self, config):
        self.config = config
        self.api_key = config.get('api_key')
        self.base_url = config.get('base_url')
        self.default_model = config.get('model', 'gpt-4')

    @abstractmethod
    def generate_text(self, prompt, model=None, temperature=1.0, max_output_tokens=8000, images=None, system_prompt=None, **kwargs):
        pass

    @abstractmethod
    def validate_config(self):
        pass

    def get_default_model(self):
        return self.default_model
