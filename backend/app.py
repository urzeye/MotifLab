"""应用启动入口。"""

from __future__ import annotations

from backend.bootstrap import AppSettings, create_app as bootstrap_create_app


def create_app():
    """兼容旧导入路径，内部委托给 bootstrap 工厂。"""
    return bootstrap_create_app()


if __name__ == "__main__":
    runtime_settings = AppSettings.from_env()
    app = create_app()
    app.run(
        host=runtime_settings.host,
        port=runtime_settings.port,
        debug=runtime_settings.debug,
    )
