import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT = int(os.getenv('FLASK_PORT', 5000))
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000').split(',')
    GOOGLE_CLOUD_API_KEY = os.getenv('GOOGLE_CLOUD_API_KEY')
    OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output')

    _image_providers_config = None

    @classmethod
    def load_image_providers_config(cls):
        if cls._image_providers_config is not None:
            return cls._image_providers_config

        config_path = Path(__file__).parent.parent / 'image_providers.yaml'

        if not config_path.exists():
            cls._image_providers_config = {
                'active_provider': 'google_genai',
                'providers': {
                    'google_genai': {
                        'type': 'google_genai',
                        'api_key_env': 'GOOGLE_CLOUD_API_KEY',
                        'model': 'gemini-3-pro-image-preview',
                        'default_aspect_ratio': '3:4'
                    }
                }
            }
            return cls._image_providers_config

        with open(config_path, 'r', encoding='utf-8') as f:
            cls._image_providers_config = yaml.safe_load(f)

        return cls._image_providers_config

    @classmethod
    def get_active_image_provider(cls):
        config = cls.load_image_providers_config()
        # 允许通过环境变量覆盖
        return os.getenv('IMAGE_PROVIDER', config.get('active_provider', 'google_genai'))

    @classmethod
    def get_image_provider_config(cls, provider_name: str = None):
        config = cls.load_image_providers_config()

        if provider_name is None:
            provider_name = cls.get_active_image_provider()

        if provider_name not in config.get('providers', {}):
            available = ', '.join(config.get('providers', {}).keys())
            raise ValueError(
                f"未找到图片生成服务商配置: {provider_name}\n"
                f"可用的服务商: {available}\n"
                "解决方案：\n"
                "1. 检查 image_providers.yaml 文件中是否包含该服务商配置\n"
                "2. 确认 providers 字段下有对应的服务商名称\n"
                "3. 或修改 active_provider 为可用的服务商名称"
            )

        provider_config = config['providers'][provider_name].copy()

        api_key_env = provider_config.get('api_key_env')
        if api_key_env:
            provider_config['api_key'] = os.getenv(api_key_env)

        return provider_config
