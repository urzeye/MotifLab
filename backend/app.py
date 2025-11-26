import logging
import sys
from flask import Flask
from flask_cors import CORS
from backend.config import Config
from backend.routes.api import api_bp


def setup_logging():
    """配置日志系统"""
    # 创建根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # 清除已有的处理器
    root_logger.handlers.clear()

    # 控制台处理器 - 详细格式
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_format = logging.Formatter(
        '\n%(asctime)s | %(levelname)-8s | %(name)s\n'
        '  └─ %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # 设置各模块的日志级别
    logging.getLogger('backend').setLevel(logging.DEBUG)
    logging.getLogger('werkzeug').setLevel(logging.INFO)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    return root_logger


def create_app():
    # 设置日志
    logger = setup_logging()
    logger.info("🚀 正在启动 红墨 AI图文生成器...")

    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, resources={
        r"/api/*": {
            "origins": Config.CORS_ORIGINS,
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"],
        }
    })

    app.register_blueprint(api_bp)

    # 启动时验证配置
    _validate_config_on_startup(logger)

    @app.route('/')
    def index():
        return {
            "message": "红墨 AI图文生成器 API",
            "version": "0.1.0",
            "endpoints": {
                "health": "/api/health",
                "outline": "POST /api/outline",
                "generate": "POST /api/generate",
                "images": "GET /api/images/<filename>"
            }
        }

    return app


def _validate_config_on_startup(logger):
    """启动时验证配置"""
    from pathlib import Path
    import yaml

    logger.info("📋 检查配置文件...")

    # 检查 text_providers.yaml
    text_config_path = Path(__file__).parent.parent / 'text_providers.yaml'
    if text_config_path.exists():
        try:
            with open(text_config_path, 'r', encoding='utf-8') as f:
                text_config = yaml.safe_load(f) or {}
            active = text_config.get('active_provider', '未设置')
            providers = list(text_config.get('providers', {}).keys())
            logger.info(f"✅ 文本生成配置: 激活={active}, 可用服务商={providers}")

            # 检查激活的服务商是否有 API Key
            if active in text_config.get('providers', {}):
                provider = text_config['providers'][active]
                if not provider.get('api_key'):
                    logger.warning(f"⚠️  文本服务商 [{active}] 未配置 API Key")
                else:
                    logger.info(f"✅ 文本服务商 [{active}] API Key 已配置")
        except Exception as e:
            logger.error(f"❌ 读取 text_providers.yaml 失败: {e}")
    else:
        logger.warning("⚠️  text_providers.yaml 不存在，将使用默认配置")

    # 检查 image_providers.yaml
    image_config_path = Path(__file__).parent.parent / 'image_providers.yaml'
    if image_config_path.exists():
        try:
            with open(image_config_path, 'r', encoding='utf-8') as f:
                image_config = yaml.safe_load(f) or {}
            active = image_config.get('active_provider', '未设置')
            providers = list(image_config.get('providers', {}).keys())
            logger.info(f"✅ 图片生成配置: 激活={active}, 可用服务商={providers}")

            # 检查激活的服务商是否有 API Key
            if active in image_config.get('providers', {}):
                provider = image_config['providers'][active]
                if not provider.get('api_key'):
                    logger.warning(f"⚠️  图片服务商 [{active}] 未配置 API Key")
                else:
                    logger.info(f"✅ 图片服务商 [{active}] API Key 已配置")
        except Exception as e:
            logger.error(f"❌ 读取 image_providers.yaml 失败: {e}")
    else:
        logger.warning("⚠️  image_providers.yaml 不存在，将使用默认配置")

    logger.info("✅ 配置检查完成")


if __name__ == '__main__':
    app = create_app()
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
