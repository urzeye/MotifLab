"""OpenAI Compatible text client"""
import time
import random
import base64
import requests
from functools import wraps
from typing import List, Optional, Union
from .base import BaseTextClient


def retry_on_429(max_retries=3, base_delay=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if '429' in str(e) or 'rate' in str(e).lower():
                        if attempt < max_retries - 1:
                            wait_time = (base_delay ** attempt) + random.uniform(0, 1)
                            time.sleep(wait_time)
                            continue
                    raise
            raise Exception(f'Retry failed after {max_retries} attempts')
        return wrapper
    return decorator


class OpenAICompatibleTextClient(BaseTextClient):
    def __init__(self, config):
        super().__init__(config)
        if not self.api_key:
            raise ValueError('API Key not configured')
        self.base_url = (self.base_url or 'https://api.openai.com').rstrip('/').rstrip('/v1')
        endpoint = config.get('endpoint_type', '/v1/chat/completions')
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        self.chat_endpoint = f'{self.base_url}{endpoint}'

    def validate_config(self):
        return bool(self.api_key)

    def _encode_image(self, image_data):
        return base64.b64encode(image_data).decode('utf-8')

    def _build_content(self, text, images=None):
        if not images:
            return text
        content = [{'type': 'text', 'text': text}]
        for img in images:
            if isinstance(img, bytes):
                base64_data = self._encode_image(img)
                image_url = f'data:image/png;base64,{base64_data}'
            else:
                image_url = img
            content.append({'type': 'image_url', 'image_url': {'url': image_url}})
        return content

    @retry_on_429(max_retries=3, base_delay=2)
    def generate_text(self, prompt, model=None, temperature=1.0, max_output_tokens=8000,
                      images=None, system_prompt=None, **kwargs):
        model = model or self.default_model
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        content = self._build_content(prompt, images)
        messages.append({'role': 'user', 'content': content})
        
        payload = {
            'model': model, 'messages': messages,
            'temperature': temperature, 'max_tokens': max_output_tokens, 'stream': False
        }
        headers = {
            'Content-Type': 'application/json', 'Accept': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        response = requests.post(self.chat_endpoint, json=payload, headers=headers, timeout=300)
        if response.status_code != 200:
            raise Exception(f'API error: {response.status_code} - {response.text[:500]}')
        result = response.json()
        if 'choices' in result and len(result['choices']) > 0:
            return result['choices'][0]['message']['content']
        raise Exception('No content in response')
