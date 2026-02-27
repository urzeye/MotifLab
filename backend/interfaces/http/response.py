"""HTTP 响应辅助函数。"""

from __future__ import annotations

from typing import Any, Dict

from flask import g, jsonify


def _build_meta() -> Dict[str, Any]:
    """构建统一响应元信息。"""
    trace_id = getattr(g, "trace_id", None)
    return {"trace_id": trace_id} if trace_id else {}


def json_response(payload: Dict[str, Any], status_code: int = 200):
    """
    输出 JSON 响应并自动附带 meta 信息。

    说明：
    - 不强制改变既有字段结构，仅补充 `meta.trace_id`
    - 若 payload 已包含 meta，则与系统 meta 合并
    """
    body = dict(payload or {})
    existing_meta = body.get("meta") if isinstance(body.get("meta"), dict) else {}
    merged_meta = dict(existing_meta)
    merged_meta.update(_build_meta())
    body["meta"] = merged_meta
    return jsonify(body), status_code
