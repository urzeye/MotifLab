"""运行时设置与环境变量解析。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _to_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except Exception:
        return default


def _to_list(value: str | None, default: List[str]) -> List[str]:
    if not value:
        return default
    items = [item.strip() for item in value.split(",")]
    return [item for item in items if item]


@dataclass(frozen=True)
class AppSettings:
    app_name: str
    app_version: str
    app_env: str
    debug: bool
    host: str
    port: int
    log_level: str
    structured_logging: bool
    cors_origins: List[str]
    rate_limit: str
    rate_limit_storage_uri: str
    project_root: Path
    frontend_dist: Path
    output_dir: Path

    @property
    def serve_frontend(self) -> bool:
        return self.frontend_dist.exists()

    @classmethod
    def from_env(cls) -> "AppSettings":
        project_root = Path(os.getenv("RENDERINK_ROOT") or Path(__file__).resolve().parents[2])
        default_cors = ["http://localhost:5173", "http://localhost:3000"]

        debug = _to_bool(os.getenv("REDINK_DEBUG"), default=True)
        log_level = (os.getenv("REDINK_LOG_LEVEL") or ("DEBUG" if debug else "INFO")).upper()

        return cls(
            app_name=(os.getenv("REDINK_APP_NAME") or "渲染AI 图文生成器").strip(),
            app_version=(os.getenv("REDINK_APP_VERSION") or "0.1.0").strip(),
            app_env=(os.getenv("APP_ENV") or "development").strip().lower(),
            debug=debug,
            host=(os.getenv("REDINK_HOST") or "0.0.0.0").strip(),
            port=_to_int(os.getenv("REDINK_PORT"), 12398),
            log_level=log_level,
            structured_logging=_to_bool(os.getenv("REDINK_STRUCTURED_LOG"), default=True),
            cors_origins=_to_list(os.getenv("REDINK_CORS_ORIGINS"), default_cors),
            rate_limit=(os.getenv("REDINK_RATE_LIMIT") or "60 per minute").strip(),
            rate_limit_storage_uri=(os.getenv("REDINK_RATE_LIMIT_STORAGE_URI") or "memory://").strip(),
            project_root=project_root,
            frontend_dist=project_root / "frontend" / "dist",
            output_dir=project_root / "output",
        )
