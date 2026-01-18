"""统一配置管理模块"""
from .settings import Settings, get_settings

# 重新导出原 config.py 中的 Config 类，保持向后兼容
import sys
from pathlib import Path

# 手动导入 backend/config.py (被包遮蔽的模块)
_config_file = Path(__file__).parent.parent / "config.py"
if _config_file.exists():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_legacy_config", _config_file)
    _legacy_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_legacy_config)
    Config = _legacy_config.Config
else:
    # Fallback: 如果找不到原文件，创建一个基本的 Config
    class Config:
        DEBUG = True
        HOST = '0.0.0.0'
        PORT = 12398
        CORS_ORIGINS = ['http://localhost:5173', 'http://localhost:3000']

__all__ = ["Settings", "get_settings", "Config"]
