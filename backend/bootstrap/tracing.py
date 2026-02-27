"""请求链路追踪能力。"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Optional
from uuid import uuid4

from flask import Flask, g, request

REQUEST_ID_HEADER = "X-Request-ID"
_TRACE_ID_CTX: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)


def _normalize_trace_id(value: str | None) -> str | None:
    """标准化外部传入的 trace_id。"""
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized[:128]


def _build_trace_id() -> str:
    """优先透传请求头 trace_id，不存在则生成新值。"""
    incoming = _normalize_trace_id(request.headers.get(REQUEST_ID_HEADER))
    return incoming or uuid4().hex


def get_trace_id() -> str | None:
    """读取当前请求上下文的 trace_id。"""
    return _TRACE_ID_CTX.get()


def register_tracing(app: Flask) -> None:
    """向 Flask 应用注册请求追踪钩子。"""

    @app.before_request
    def _set_trace_id() -> None:
        trace_id = _build_trace_id()
        g.trace_id = trace_id
        _TRACE_ID_CTX.set(trace_id)

    @app.after_request
    def _inject_trace_id_header(response):
        trace_id = getattr(g, "trace_id", None) or _TRACE_ID_CTX.get() or uuid4().hex
        response.headers[REQUEST_ID_HEADER] = trace_id
        return response

    @app.teardown_request
    def _clear_trace_id(_error) -> None:
        _TRACE_ID_CTX.set(None)
