"""SQLAlchemy 概念历史仓储实现。"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import func, select

from backend.domain.ports import ConceptRepositoryPort

from .json_utils import dump_json, load_json
from .models import ConceptRecordModel
from .session import session_scope


def _to_iso(dt: datetime | None) -> str:
    """日期时间转 ISO 字符串。"""
    return dt.isoformat() if isinstance(dt, datetime) else ""


class SqlAlchemyConceptRepository(ConceptRepositoryPort):
    """基于 SQLAlchemy 的概念历史仓储。"""

    def create_record(
        self,
        title: str,
        article: str,
        task_id: str,
        style: Optional[str] = None,
    ) -> str:
        record_id = str(uuid.uuid4())
        article_text = str(article or "")
        article_preview = article_text[:200] + "..." if len(article_text) > 200 else article_text

        with session_scope() as session:
            session.add(
                ConceptRecordModel(
                    id=record_id,
                    title=(str(title or "").strip() or article_text[:20] or "未命名主题"),
                    article_preview=article_preview,
                    article_full=article_text,
                    status="in_progress",
                    task_id=str(task_id or ""),
                    style=style,
                    thumbnail=None,
                    image_count=0,
                    pipeline_data_json=dump_json(
                        {
                            "analyze": None,
                            "map": None,
                            "design": None,
                            "generate": None,
                        },
                        {},
                    ),
                )
            )
        return record_id

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        with session_scope() as session:
            model = session.get(ConceptRecordModel, record_id)
            if model is None:
                return None
            return self._to_detail(model)

    def update_record(
        self,
        record_id: str,
        title: Optional[str] = None,
        status: Optional[str] = None,
        thumbnail: Optional[str] = None,
        image_count: Optional[int] = None,
        pipeline_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        with session_scope() as session:
            model = session.get(ConceptRecordModel, record_id)
            if model is None:
                return False

            if title is not None:
                model.title = str(title).strip() or model.title
            if status is not None:
                model.status = str(status).strip() or model.status
            if thumbnail is not None:
                model.thumbnail = str(thumbnail) if thumbnail else None
            if image_count is not None:
                model.image_count = max(0, int(image_count))
            if isinstance(pipeline_data, dict):
                old_data = load_json(model.pipeline_data_json, {})
                merged = dict(old_data if isinstance(old_data, dict) else {})
                merged.update(pipeline_data)
                model.pipeline_data_json = dump_json(merged, {})

            model.updated_at = datetime.now(timezone.utc)
            session.add(model)
            return True

    def delete_record(self, record_id: str) -> bool:
        with session_scope() as session:
            model = session.get(ConceptRecordModel, record_id)
            if model is None:
                return False
            session.delete(model)
            return True

    def list_records(self, page: int = 1, page_size: int = 20, status: Optional[str] = None) -> Dict[str, Any]:
        safe_page = max(1, int(page or 1))
        safe_page_size = max(1, min(100, int(page_size or 20)))

        with session_scope() as session:
            stmt = select(ConceptRecordModel)
            count_stmt = select(func.count(ConceptRecordModel.id))

            if status and status not in {"all", "ALL"}:
                stmt = stmt.where(ConceptRecordModel.status == status)
                count_stmt = count_stmt.where(ConceptRecordModel.status == status)

            total = int(session.execute(count_stmt).scalar() or 0)
            total_pages = (total + safe_page_size - 1) // safe_page_size

            stmt = (
                stmt.order_by(ConceptRecordModel.created_at.desc())
                .offset((safe_page - 1) * safe_page_size)
                .limit(safe_page_size)
            )
            rows = session.execute(stmt).scalars().all()
            records = [self._to_summary(item) for item in rows]

        return {
            "records": records,
            "total": total,
            "page": safe_page,
            "page_size": safe_page_size,
            "total_pages": total_pages,
        }

    def get_record_by_task_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        with session_scope() as session:
            stmt = select(ConceptRecordModel).where(ConceptRecordModel.task_id == task_id).limit(1)
            model = session.execute(stmt).scalars().first()
            if model is None:
                return None
            return self._to_detail(model)

    def repair_record_images(self, record_id: str) -> bool:
        """数据库模式下不需要扫描文件系统，返回记录存在性。"""
        with session_scope() as session:
            return session.get(ConceptRecordModel, record_id) is not None

    def repair_all_records(self) -> Dict[str, Any]:
        """数据库模式下无需修复，返回空修复结果。"""
        with session_scope() as session:
            total = int(session.execute(select(func.count(ConceptRecordModel.id))).scalar() or 0)
        return {
            "repaired": 0,
            "failed": 0,
            "total": total,
            "message": "数据库模式无需执行本地图片修复",
        }

    @staticmethod
    def _to_summary(model: ConceptRecordModel) -> Dict[str, Any]:
        return {
            "id": model.id,
            "title": model.title,
            "created_at": _to_iso(model.created_at),
            "updated_at": _to_iso(model.updated_at),
            "status": model.status,
            "task_id": model.task_id,
            "style": model.style,
            "article_preview": model.article_preview,
            "thumbnail": model.thumbnail,
            "image_count": int(model.image_count or 0),
        }

    @staticmethod
    def _to_detail(model: ConceptRecordModel) -> Dict[str, Any]:
        pipeline_data = load_json(model.pipeline_data_json, {})
        return {
            "id": model.id,
            "title": model.title,
            "created_at": _to_iso(model.created_at),
            "updated_at": _to_iso(model.updated_at),
            "status": model.status,
            "task_id": model.task_id,
            "style": model.style,
            "article_preview": model.article_preview,
            "article_full": model.article_full,
            "thumbnail": model.thumbnail,
            "image_count": int(model.image_count or 0),
            "pipeline_data": pipeline_data if isinstance(pipeline_data, dict) else {},
        }
