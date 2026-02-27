"""运行时设置与环境变量解析。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

DEFAULT_APP_NAME = "MotifLab"
DEFAULT_APP_VERSION = "0.1.0"


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


def _parse_toml_string(value: str) -> str | None:
    value = value.strip()
    if len(value) < 2:
        return None
    quote = value[0]
    if quote not in {"'", '"'} or value[-1] != quote:
        return None
    return value[1:-1].strip()


def _read_project_metadata(project_root: Path) -> tuple[str, str]:
    pyproject = project_root / "pyproject.toml"
    if not pyproject.exists():
        return DEFAULT_APP_NAME, DEFAULT_APP_VERSION

    try:
        content = pyproject.read_text(encoding="utf-8")
    except Exception:
        return DEFAULT_APP_NAME, DEFAULT_APP_VERSION

    in_project_section = False
    project_name: str | None = None
    project_description: str | None = None
    project_version: str | None = None

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            in_project_section = line == "[project]"
            continue
        if not in_project_section or "=" not in line:
            continue

        key, value = line.split("=", 1)
        parsed = _parse_toml_string(value)
        if parsed is None:
            continue

        normalized_key = key.strip()
        if normalized_key == "name":
            project_name = parsed
        elif normalized_key == "description":
            project_description = parsed
        elif normalized_key == "version":
            project_version = parsed

    app_name = (project_description or project_name or DEFAULT_APP_NAME).strip() or DEFAULT_APP_NAME
    app_version = (project_version or DEFAULT_APP_VERSION).strip() or DEFAULT_APP_VERSION
    return app_name, app_version


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
        project_root = Path(
            os.getenv("MOTIFLAB_ROOT") or os.getenv("RENDERINK_ROOT") or Path(__file__).resolve().parents[2]
        )
        default_app_name, default_app_version = _read_project_metadata(project_root)
        default_cors = ["http://localhost:5173", "http://localhost:3000"]

        debug = _to_bool(os.getenv("MOTIFLAB_DEBUG"), default=True)
        log_level = (os.getenv("MOTIFLAB_LOG_LEVEL") or ("DEBUG" if debug else "INFO")).upper()

        return cls(
            app_name=(os.getenv("MOTIFLAB_APP_NAME") or default_app_name).strip(),
            app_version=(os.getenv("MOTIFLAB_APP_VERSION") or default_app_version).strip(),
            app_env=(os.getenv("APP_ENV") or "development").strip().lower(),
            debug=debug,
            host=(os.getenv("MOTIFLAB_HOST") or "0.0.0.0").strip(),
            port=_to_int(os.getenv("MOTIFLAB_PORT"), 12398),
            log_level=log_level,
            structured_logging=_to_bool(os.getenv("MOTIFLAB_STRUCTURED_LOG"), default=True),
            cors_origins=_to_list(os.getenv("MOTIFLAB_CORS_ORIGINS"), default_cors),
            rate_limit=(os.getenv("MOTIFLAB_RATE_LIMIT") or "60 per minute").strip(),
            rate_limit_storage_uri=(os.getenv("MOTIFLAB_RATE_LIMIT_STORAGE_URI") or "memory://").strip(),
            project_root=project_root,
            frontend_dist=project_root / "frontend" / "dist",
            output_dir=project_root / "output",
        )
