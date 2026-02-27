"""SQLAlchemy 发布记录仓储实现。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select

from backend.domain.ports import PublishRepositoryPort

from .json_utils import dump_json, load_json
from .models import PublishRecordModel
from .session import session_scope


def _to_iso(dt: datetime | None) -> str:
    """日期时间转 ISO 字符串。"""
    return dt.isoformat() if isinstance(dt, datetime) else ""


class SqlAlchemyPublishRepository(PublishRepositoryPort):
    """基于 SQLAlchemy 的发布记录仓储。"""

    def create_record(
        self,
        title: str,
        content: str,
        images: List[str],
        tags: Optional[List[str]] = None,
        status: str = "pending",
        message: str = "",
        post_url: Optional[str] = None,
    ) -> int:
        with session_scope() as session:
            model = PublishRecordModel(
                title=str(title or "").strip(),
                content=str(content or ""),
                images_json=dump_json(images if isinstance(images, list) else [], []),
                tags_json=dump_json(tags if isinstance(tags, list) else [], []),
                status=str(status or "pending"),
                message=str(message or ""),
                post_url=post_url,
            )
            session.add(model)
            session.flush()
            return int(model.id)

    def update_record(
        self,
        record_id: int,
        *,
        status: Optional[str] = None,
        message: Optional[str] = None,
        post_url: Optional[str] = None,
    ) -> bool:
        with session_scope() as session:
            model = session.get(PublishRecordModel, int(record_id))
            if model is None:
                return False

            if status is not None:
                model.status = str(status)
            if message is not None:
                model.message = str(message)
            if post_url is not None:
                model.post_url = post_url
            model.updated_at = datetime.now(timezone.utc)
            session.add(model)
            return True

    def get_record(self, record_id: int) -> Optional[Dict[str, Any]]:
        with session_scope() as session:
            model = session.get(PublishRecordModel, int(record_id))
            if model is None:
                return None
            return self._to_dict(model)

    def list_records(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        safe_page = max(1, int(page or 1))
        safe_page_size = max(1, min(100, int(page_size or 20)))

        with session_scope() as session:
            stmt = select(PublishRecordModel)
            count_stmt = select(func.count(PublishRecordModel.id))
            if status and status not in {"all", "ALL"}:
                stmt = stmt.where(PublishRecordModel.status == status)
                count_stmt = count_stmt.where(PublishRecordModel.status == status)

            total = int(session.execute(count_stmt).scalar() or 0)
            total_pages = (total + safe_page_size - 1) // safe_page_size

            rows = session.execute(
                stmt.order_by(PublishRecordModel.created_at.desc())
                .offset((safe_page - 1) * safe_page_size)
                .limit(safe_page_size)
            ).scalars().all()

            return {
                "records": [self._to_dict(row) for row in rows],
                "total": total,
                "page": safe_page,
                "page_size": safe_page_size,
                "total_pages": total_pages,
            }

    @staticmethod
    def _to_dict(model: PublishRecordModel) -> Dict[str, Any]:
        return {
            "id": int(model.id),
            "title": model.title,
            "content": model.content,
            "images": load_json(model.images_json, []),
            "tags": load_json(model.tags_json, []),
            "status": model.status,
            "message": model.message,
            "post_url": model.post_url,
            "created_at": _to_iso(model.created_at),
            "updated_at": _to_iso(model.updated_at),
        }
