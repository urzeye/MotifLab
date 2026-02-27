"""Google GenAI text client"""
import time
import random
from functools import wraps
from google import genai
from google.genai import types
from .base import BaseTextClient


def retry_on_error(max_retries=3, base_delay=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    err = str(e).lower()
                    non_retryable = ['401', 'unauthenticated', '403', 'permission_denied', '404', 'not_found']
                    if any(x in err for x in non_retryable):
                        raise
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 10) + random.uniform(0, 1)
                        time.sleep(wait_time)
                        continue
                    raise
            raise Exception('Retry failed')
        return wrapper
    return decorator


class GoogleGenAITextClient(BaseTextClient):
    def __init__(self, config):
        super().__init__(config)
        if not self.api_key:
            raise ValueError('Google GenAI API Key not configured')
        client_kwargs = {'api_key': self.api_key, 'vertexai': False}
        if self.base_url:
            client_kwargs['http_options'] = {'base_url': self.base_url, 'api_version': 'v1beta'}
        self.client = genai.Client(**client_kwargs)
        self.safety_settings = [
            types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold='OFF'),
            types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold='OFF'),
            types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='OFF'),
            types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='OFF'),
        ]

    def validate_config(self):
        return bool(self.api_key)

    @retry_on_error(max_retries=3, base_delay=2)
    def generate_text(self, prompt, model=None, temperature=1.0, max_output_tokens=8000,
                      images=None, system_prompt=None, use_search=False, use_thinking=False, **kwargs):
        model = model or self.default_model
        parts = [types.Part(text=prompt)]
        if images:
            for img_data in images:
                if isinstance(img_data, bytes):
                    parts.append(types.Part(inline_data=types.Blob(mime_type='image/png', data=img_data)))
        contents = [types.Content(role='user', parts=parts)]
        config_kwargs = {
            'temperature': temperature, 'top_p': 0.95,
            'max_output_tokens': max_output_tokens, 'safety_settings': self.safety_settings
        }
        if use_search:
            config_kwargs['tools'] = [types.Tool(google_search=types.GoogleSearch())]
        if use_thinking:
            config_kwargs['thinking_config'] = types.ThinkingConfig(thinking_level='HIGH')
        config = types.GenerateContentConfig(**config_kwargs)
        result = ''
        for chunk in self.client.models.generate_content_stream(model=model, contents=contents, config=config):
            if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                result += chunk.text
        return result
