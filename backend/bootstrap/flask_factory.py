"""Flask 应用工厂与启动装配。"""

from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask, request, send_from_directory

from backend.config import Config, get_config_service
from backend.middleware import authenticate_request, is_auth_enabled
from backend.routes import register_routes

from .container import build_container
from .logging import configure_logging
from .settings import AppSettings
from .tracing import register_tracing


def _create_flask_app(settings: AppSettings, logger: logging.Logger) -> Flask:
    """根据运行环境创建 Flask 实例。"""
    if settings.serve_frontend:
        logger.info("📦 检测到前端构建产物，启用静态文件托管模式")
        return Flask(
            __name__,
            static_folder=str(settings.frontend_dist),
            static_url_path="",
        )

    logger.info("🔧 开发模式，前端请单独启动")
    return Flask(__name__)


def _configure_cors(app: Flask, settings: AppSettings, logger: logging.Logger) -> None:
    """配置 API 跨域。"""
    try:
        from flask_cors import CORS
    except Exception:
        logger.warning("⚠️ flask-cors 未安装，已跳过 CORS 配置")
        return

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": settings.cors_origins,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization", "X-Request-ID"],
            }
        },
    )


def _configure_auth_guard(app: Flask, logger: logging.Logger) -> None:
    """注册 API 鉴权前置拦截。"""
    if is_auth_enabled():
        logger.warning("🔒 已启用 API 访问令牌认证（REDINK_AUTH_TOKEN）")
    else:
        logger.info("🔓 未启用 API 访问令牌认证（REDINK_AUTH_TOKEN 未设置）")

    @app.before_request
    def _api_auth_guard():
        if not request.path.startswith("/api/"):
            return None
        # 健康检查保持公开，方便外部探活
        return authenticate_request(exempt_paths={"/api/health"})


def _configure_rate_limiter(app: Flask, settings: AppSettings, logger: logging.Logger) -> None:
    """初始化全局限流组件。"""
    try:
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address

        limiter = Limiter(
            get_remote_address,
            app=app,
            default_limits=[settings.rate_limit],
            storage_uri=settings.rate_limit_storage_uri,
        )
        app.limiter = limiter
        logger.info(f"🚦 已启用全局限流: {settings.rate_limit}")
    except Exception as exc:
        logger.warning(f"⚠️ 限流组件初始化失败，已跳过: {exc}")


def _register_output_route(app: Flask, output_dir: Path) -> None:
    """注册生成产物静态访问路由。"""

    @app.route("/output/<path:filename>")
    def _serve_output(filename):
        return send_from_directory(str(output_dir), filename)


def _register_root_routes(app: Flask, settings: AppSettings) -> None:
    """注册根路由与前端回退路由。"""
    if settings.serve_frontend:

        @app.route("/")
        def _serve_index():
            return send_from_directory(app.static_folder, "index.html")

        @app.errorhandler(404)
        def _fallback(_error):
            if request.path.startswith("/api/"):
                return {"success": False, "error": "Not found"}, 404
            return send_from_directory(app.static_folder, "index.html")

        return

    @app.route("/")
    def _index():
        return {
            "message": "渲染AI 图文生成器 API",
            "version": "0.1.0",
            "endpoints": {
                "health": "/api/health",
                "outline": "POST /api/outline",
                "generate": "POST /api/generate",
                "images": "GET /api/images/<filename>",
            },
        }


def _validate_config_on_startup(logger: logging.Logger) -> None:
    """启动时验证关键配置可用性。"""
    config_service = get_config_service()

    logger.info("📋 检查配置存储...")
    try:
        storage_mode = config_service.get_config_storage_mode()
    except Exception:
        storage_mode = "yaml"
    logger.info(f"📦 配置存储模式: {storage_mode}")

    try:
        text_config = config_service.load_text_providers_config()
        active = text_config.get("active_provider", "未设置")
        providers = list((text_config.get("providers") or {}).keys())
        logger.info(f"✅ 文本生成配置: 激活={active}, 可用服务商={providers}")
        if active in (text_config.get("providers") or {}):
            provider = text_config["providers"][active]
            if not provider.get("api_key"):
                logger.warning(f"⚠️  文本服务商 [{active}] 未配置 API Key")
            else:
                logger.info(f"✅ 文本服务商 [{active}] API Key 已配置")
    except Exception as exc:
        logger.error(f"❌ 读取文本配置失败: {exc}")

    try:
        image_config = config_service.load_image_providers_config()
        active = image_config.get("active_provider", "未设置")
        providers = list((image_config.get("providers") or {}).keys())
        logger.info(f"✅ 图片生成配置: 激活={active}, 可用服务商={providers}")
        if active in (image_config.get("providers") or {}):
            provider = image_config["providers"][active]
            if not provider.get("api_key"):
                logger.warning(f"⚠️  图片服务商 [{active}] 未配置 API Key")
            else:
                logger.info(f"✅ 图片服务商 [{active}] API Key 已配置")
    except Exception as exc:
        logger.error(f"❌ 读取图片配置失败: {exc}")

    logger.info("✅ 配置检查完成")


def create_app(settings: AppSettings | None = None) -> Flask:
    """创建并装配 Flask 应用。"""
    runtime_settings = settings or AppSettings.from_env()
    logger = configure_logging(runtime_settings)
    logger.info("🚀 正在启动 渲染AI 图文生成器...")

    app = _create_flask_app(runtime_settings, logger)
    app.extensions["backend_container"] = build_container()

    app.config.from_object(Config)
    app.config.update(
        DEBUG=runtime_settings.debug,
        HOST=runtime_settings.host,
        PORT=runtime_settings.port,
        CORS_ORIGINS=runtime_settings.cors_origins,
        OUTPUT_DIR=str(runtime_settings.output_dir),
    )

    _configure_cors(app, runtime_settings, logger)
    register_tracing(app)
    _configure_auth_guard(app, logger)
    _configure_rate_limiter(app, runtime_settings, logger)

    register_routes(app)
    _register_output_route(app, runtime_settings.output_dir)
    _validate_config_on_startup(logger)
    _register_root_routes(app, runtime_settings)

    return app
