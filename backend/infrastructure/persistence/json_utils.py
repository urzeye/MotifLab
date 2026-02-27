"""JSON 字段序列化辅助函数。"""

from __future__ import annotations

import json
from typing import Any


def dump_json(value: Any, default: Any) -> str:
    """将对象安全序列化为 JSON 字符串。"""
    try:
        return json.dumps(value if value is not None else default, ensure_ascii=False)
    except Exception:
        return json.dumps(default, ensure_ascii=False)


def load_json(text: str | None, default: Any) -> Any:
    """将 JSON 字符串安全反序列化为对象。"""
    if not text:
        return default
    try:
        data = json.loads(text)
        return data if data is not None else default
    except Exception:
        return default
