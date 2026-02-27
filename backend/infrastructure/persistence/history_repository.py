"""SQLAlchemy 图文历史仓储实现。"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select

from backend.domain.ports import HistoryRepositoryPort

from .json_utils import dump_json, load_json
from .models import HistoryRecordModel
from .session import session_scope


def _to_iso(dt: datetime | None) -> str:
    """日期时间转 ISO 字符串。"""
    return dt.isoformat() if isinstance(dt, datetime) else ""


def _normalize_content(content: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """规范化内容字段结构。"""
    if not isinstance(content, dict):
        return {"titles": [], "copywriting": "", "tags": []}

    titles = content.get("titles", [])
    copywriting = content.get("copywriting", "")
    tags = content.get("tags", [])

    if isinstance(titles, str):
        titles = [titles]
    if not isinstance(titles, list):
        titles = []

    if not isinstance(copywriting, str):
        copywriting = str(copywriting or "")

    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    if not isinstance(tags, list):
        tags = []

    return {
        "titles": titles,
        "copywriting": copywriting,
        "tags": tags,
    }


class SqlAlchemyHistoryRepository(HistoryRepositoryPort):
    """基于 SQLAlchemy 的历史记录仓储。"""

    def create_record(
        self,
        topic: str,
        outline: Dict[str, Any],
        task_id: Optional[str] = None,
        content: Optional[Dict[str, Any]] = None,
    ) -> str:
        record_id = str(uuid.uuid4())
        outline_obj = outline if isinstance(outline, dict) else {}
        page_count = len(outline_obj.get("pages", [])) if isinstance(outline_obj.get("pages"), list) else 0
        images_obj = {"task_id": task_id, "generated": []}

        with session_scope() as session:
            session.add(
                HistoryRecordModel(
                    id=record_id,
                    title=str(topic or "").strip(),
                    topic=str(topic or "").strip(),
                    outline_json=dump_json(outline_obj, {}),
                    images_json=dump_json(images_obj, {}),
                    content_json=dump_json(_normalize_content(content), {}),
                    status="draft",
                    thumbnail=None,
                    page_count=page_count,
                    task_id=task_id,
                )
            )
        return record_id

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        with session_scope() as session:
            model = session.get(HistoryRecordModel, record_id)
            if model is None:
                return None
            return self._to_detail(model)

    def record_exists(self, record_id: str) -> bool:
        with session_scope() as session:
            return session.get(HistoryRecordModel, record_id) is not None

    def update_record(
        self,
        record_id: str,
        outline: Optional[Dict[str, Any]] = None,
        images: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        thumbnail: Optional[str] = None,
        content: Optional[Dict[str, Any]] = None,
    ) -> bool:
        with session_scope() as session:
            model = session.get(HistoryRecordModel, record_id)
            if model is None:
                return False

            if isinstance(outline, dict):
                model.outline_json = dump_json(outline, {})
                pages = outline.get("pages", [])
                model.page_count = len(pages) if isinstance(pages, list) else model.page_count
            if isinstance(images, dict):
                existing_images = load_json(model.images_json, {})
                merged = dict(existing_images if isinstance(existing_images, dict) else {})
                merged.update(images)
                model.images_json = dump_json(merged, {})
                if isinstance(merged.get("task_id"), str):
                    model.task_id = merged.get("task_id")
            if status:
                model.status = str(status)
            if thumbnail is not None:
                model.thumbnail = str(thumbnail) if thumbnail else None
            if content is not None:
                merged_content = _normalize_content(content)
                model.content_json = dump_json(merged_content, {})

            model.updated_at = datetime.now(timezone.utc)
            session.add(model)
            return True

    def delete_record(self, record_id: str) -> bool:
        with session_scope() as session:
            model = session.get(HistoryRecordModel, record_id)
            if model is None:
                return False
            session.delete(model)
            return True

    def list_records(self, page: int = 1, page_size: int = 20, status: Optional[str] = None) -> Dict[str, Any]:
        safe_page = max(1, int(page or 1))
        safe_page_size = max(1, min(100, int(page_size or 20)))

        with session_scope() as session:
            stmt = select(HistoryRecordModel)
            count_stmt = select(func.count(HistoryRecordModel.id))

            if status and status not in {"all", "ALL"}:
                stmt = stmt.where(HistoryRecordModel.status == status)
                count_stmt = count_stmt.where(HistoryRecordModel.status == status)

            total = int(session.execute(count_stmt).scalar() or 0)
            total_pages = (total + safe_page_size - 1) // safe_page_size

            stmt = (
                stmt.order_by(HistoryRecordModel.created_at.desc())
                .offset((safe_page - 1) * safe_page_size)
                .limit(safe_page_size)
            )
            rows = session.execute(stmt).scalars().all()
            records = [self._to_summary(row) for row in rows]

        return {
            "records": records,
            "total": total,
            "page": safe_page,
            "page_size": safe_page_size,
            "total_pages": total_pages,
        }

    def search_records(self, keyword: str) -> List[Dict[str, Any]]:
        q = str(keyword or "").strip()
        if not q:
            return []
        like = f"%{q}%"

        with session_scope() as session:
            stmt = (
                select(HistoryRecordModel)
                .where(
                    HistoryRecordModel.title.like(like)
                    | HistoryRecordModel.topic.like(like)
                )
                .order_by(HistoryRecordModel.created_at.desc())
            )
            rows = session.execute(stmt).scalars().all()
            return [self._to_summary(row) for row in rows]

    def get_statistics(self) -> Dict[str, Any]:
        with session_scope() as session:
            total = int(session.execute(select(func.count(HistoryRecordModel.id))).scalar() or 0)
            grouped = session.execute(
                select(HistoryRecordModel.status, func.count(HistoryRecordModel.id)).group_by(HistoryRecordModel.status)
            ).all()

        by_status = {str(status): int(count) for status, count in grouped}
        return {
            "total": total,
            "by_status": by_status,
        }

    @staticmethod
    def _to_summary(model: HistoryRecordModel) -> Dict[str, Any]:
        return {
            "id": model.id,
            "title": model.title,
            "created_at": _to_iso(model.created_at),
            "updated_at": _to_iso(model.updated_at),
            "status": model.status,
            "thumbnail": model.thumbnail,
            "page_count": int(model.page_count or 0),
            "task_id": model.task_id,
        }

    @staticmethod
    def _to_detail(model: HistoryRecordModel) -> Dict[str, Any]:
        outline = load_json(model.outline_json, {})
        images = load_json(model.images_json, {})
        content = load_json(model.content_json, {"titles": [], "copywriting": "", "tags": []})
        return {
            "id": model.id,
            "title": model.title,
            "created_at": _to_iso(model.created_at),
            "updated_at": _to_iso(model.updated_at),
            "outline": outline if isinstance(outline, dict) else {},
            "images": images if isinstance(images, dict) else {},
            "content": content if isinstance(content, dict) else {"titles": [], "copywriting": "", "tags": []},
            "status": model.status,
            "thumbnail": model.thumbnail,
        }
