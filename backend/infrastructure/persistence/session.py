"""SQLAlchemy 会话与引擎管理。"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker

_ENGINE: Engine | None = None
_SESSION_FACTORY: scoped_session | None = None

DB_URL_ENV = "REDINK_DATABASE_URL"
DB_URL_FALLBACK_ENV = "DATABASE_URL"


def _project_root() -> Path:
    """获取项目根目录。"""
    return Path(__file__).resolve().parents[3]


def _default_sqlite_url() -> str:
    """生成默认 SQLite 连接串。"""
    db_file = _project_root() / "data" / "redink.db"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_file.as_posix()}"


def get_database_url() -> str:
    """读取数据库连接串，未配置时回退 SQLite。"""
    url = (os.getenv(DB_URL_ENV) or os.getenv(DB_URL_FALLBACK_ENV) or "").strip()
    if url:
        return url
    return _default_sqlite_url()


def get_engine() -> Engine:
    """获取全局 SQLAlchemy 引擎单例。"""
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE

    database_url = get_database_url()
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    _ENGINE = create_engine(
        database_url,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    return _ENGINE


def get_session_factory() -> scoped_session:
    """获取全局 Session 工厂。"""
    global _SESSION_FACTORY
    if _SESSION_FACTORY is not None:
        return _SESSION_FACTORY

    _SESSION_FACTORY = scoped_session(
        sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
            expire_on_commit=False,
            class_=Session,
        )
    )
    return _SESSION_FACTORY


@contextmanager
def session_scope() -> Iterator[Session]:
    """提供带提交/回滚的会话上下文。"""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database_schema() -> None:
    """初始化数据库表结构（基线模式）。"""
    from .base import Base
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())


def reset_database_engine() -> None:
    """重置全局引擎与会话工厂（用于测试隔离）。"""
    global _ENGINE, _SESSION_FACTORY
    if _SESSION_FACTORY is not None:
        _SESSION_FACTORY.remove()
    if _ENGINE is not None:
        _ENGINE.dispose()
    _ENGINE = None
    _SESSION_FACTORY = None
