"""模板服务：读取并查询 data/template.json。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TemplateService:
    """提供模板数据加载、搜索、分类统计等能力。"""

    def __init__(self) -> None:
        self._project_root = Path(__file__).resolve().parents[3]
        self._template_file = self._project_root / "data" / "template.json"
        self._templates: List[Dict[str, Any]] = []
        self._mtime: Optional[float] = None

    def _ensure_loaded(self) -> None:
        """按文件修改时间增量加载，避免每次请求都读盘。"""
        if not self._template_file.exists():
            logger.warning("模板文件不存在: %s", self._template_file)
            self._templates = []
            self._mtime = None
            return

        stat = self._template_file.stat()
        if self._mtime is not None and self._mtime == stat.st_mtime:
            return

        with self._template_file.open("r", encoding="utf-8") as f:
            raw = json.load(f) or {}

        templates = raw.get("templates", [])
        if not isinstance(templates, list):
            logger.warning("模板文件格式异常：templates 字段不是数组")
            templates = []

        # 默认按使用量降序，热门模板优先展示
        templates.sort(key=lambda item: int(item.get("usageCount", 0) or 0), reverse=True)

        self._templates = templates
        self._mtime = stat.st_mtime
        logger.info("模板数据已加载，数量=%s", len(self._templates))

    def list_templates(
        self,
        q: str = "",
        category: str = "",
        limit: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """模板列表查询：支持关键词和分类过滤。"""
        self._ensure_loaded()
        keyword = q.strip().lower()
        category_name = category.strip()

        results = self._templates

        if category_name and category_name not in ("全部", "all", "ALL"):
            results = [item for item in results if item.get("category", "") == category_name]

        if keyword:
            def _match(item: Dict[str, Any]) -> bool:
                title = str(item.get("title", "")).lower()
                desc = str(item.get("description", "")).lower()
                prompt = str(item.get("prompt", "")).lower()
                tags = " ".join(str(tag) for tag in item.get("tags", [])).lower()
                return keyword in title or keyword in desc or keyword in prompt or keyword in tags

            results = [item for item in results if _match(item)]

        total = len(results)
        if isinstance(limit, int) and limit > 0:
            results = results[:limit]

        return results, total

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """按 ID 获取模板详情。"""
        self._ensure_loaded()
        target_id = template_id.strip()
        if not target_id:
            return None

        for item in self._templates:
            if item.get("id") == target_id:
                return item
        return None

    def list_categories(self) -> List[Dict[str, Any]]:
        """返回分类及数量统计。"""
        self._ensure_loaded()
        counter: Dict[str, int] = {}
        for item in self._templates:
            category = str(item.get("category") or "未分类")
            counter[category] = counter.get(category, 0) + 1

        # 按数量降序，同数量按名称升序
        sorted_items = sorted(counter.items(), key=lambda x: (-x[1], x[0]))
        return [{"name": name, "count": count} for name, count in sorted_items]


_template_service: Optional[TemplateService] = None


def get_template_service() -> TemplateService:
    global _template_service
    if _template_service is None:
        _template_service = TemplateService()
    return _template_service

