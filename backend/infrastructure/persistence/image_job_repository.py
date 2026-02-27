"""SQLAlchemy 图片任务仓储实现。"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select

from backend.domain.ports import ImageJobRepositoryPort

from .json_utils import dump_json, load_json
from .models import ImageJobItemModel, ImageJobModel
from .session import session_scope


def _to_iso(dt: datetime | None) -> str:
    """日期时间转 ISO 字符串。"""
    return dt.isoformat() if isinstance(dt, datetime) else ""


class SqlAlchemyImageJobRepository(ImageJobRepositoryPort):
    """基于 SQLAlchemy 的图片任务仓储。"""

    def create_job(
        self,
        payload: Dict[str, Any],
        *,
        status: str = "queued",
    ) -> str:
        job_id = f"job_{uuid.uuid4().hex[:16]}"
        pages = payload.get("pages")
        total_pages = len(pages) if isinstance(pages, list) else 0

        with session_scope() as session:
            session.add(
                ImageJobModel(
                    id=job_id,
                    status=str(status or "queued"),
                    payload_json=dump_json(payload if isinstance(payload, dict) else {}, {}),
                    result_json=dump_json({"images": []}, {}),
                    total_pages=total_pages,
                    completed_pages=0,
                    failed_pages=0,
                    cancel_requested=False,
                )
            )
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with session_scope() as session:
            model = session.get(ImageJobModel, job_id)
            if model is None:
                return None
            return self._to_dict(model, items=self.list_job_items(job_id))

    def list_jobs(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        safe_page = max(1, int(page or 1))
        safe_page_size = max(1, min(100, int(page_size or 20)))

        with session_scope() as session:
            stmt = select(ImageJobModel)
            count_stmt = select(func.count(ImageJobModel.id))

            if status and status not in {"all", "ALL"}:
                stmt = stmt.where(ImageJobModel.status == status)
                count_stmt = count_stmt.where(ImageJobModel.status == status)

            total = int(session.execute(count_stmt).scalar() or 0)
            total_pages = (total + safe_page_size - 1) // safe_page_size

            rows = session.execute(
                stmt.order_by(ImageJobModel.created_at.desc())
                .offset((safe_page - 1) * safe_page_size)
                .limit(safe_page_size)
            ).scalars().all()

            return {
                "records": [self._to_dict(row, include_items=False) for row in rows],
                "total": total,
                "page": safe_page,
                "page_size": safe_page_size,
                "total_pages": total_pages,
            }

    def update_job(
        self,
        job_id: str,
        fields: Dict[str, Any],
    ) -> bool:
        if not isinstance(fields, dict):
            return False

        with session_scope() as session:
            model = session.get(ImageJobModel, job_id)
            if model is None:
                return False

            for key, value in fields.items():
                if key == "status" and value is not None:
                    model.status = str(value)
                elif key == "task_id":
                    model.task_id = str(value) if value else None
                elif key == "error":
                    model.error = str(value) if value else None
                elif key == "cancel_requested":
                    model.cancel_requested = bool(value)
                elif key == "total_pages" and value is not None:
                    model.total_pages = max(0, int(value))
                elif key == "completed_pages" and value is not None:
                    model.completed_pages = max(0, int(value))
                elif key == "failed_pages" and value is not None:
                    model.failed_pages = max(0, int(value))
                elif key == "payload":
                    model.payload_json = dump_json(value if isinstance(value, dict) else {}, {})
                elif key == "result":
                    model.result_json = dump_json(value if isinstance(value, dict) else {}, {})
                elif key == "started_at":
                    model.started_at = value if isinstance(value, datetime) else None
                elif key == "finished_at":
                    model.finished_at = value if isinstance(value, datetime) else None

            model.updated_at = datetime.now(timezone.utc)
            session.add(model)
            return True

    def mark_cancel_requested(self, job_id: str) -> bool:
        return self.update_job(job_id, {"cancel_requested": True})

    def upsert_job_item(
        self,
        job_id: str,
        page_index: int,
        fields: Dict[str, Any],
    ) -> bool:
        with session_scope() as session:
            stmt = (
                select(ImageJobItemModel)
                .where(ImageJobItemModel.job_id == job_id)
                .where(ImageJobItemModel.page_index == int(page_index))
                .limit(1)
            )
            model = session.execute(stmt).scalars().first()
            if model is None:
                model = ImageJobItemModel(
                    job_id=job_id,
                    page_index=int(page_index),
                    status="queued",
                )

            if isinstance(fields, dict):
                if "status" in fields and fields.get("status") is not None:
                    model.status = str(fields.get("status"))
                if "image_url" in fields:
                    image_url = fields.get("image_url")
                    model.image_url = str(image_url) if image_url else None
                if "error" in fields:
                    error = fields.get("error")
                    model.error = str(error) if error else None

            model.updated_at = datetime.now(timezone.utc)
            session.add(model)
            return True

    def list_job_items(self, job_id: str) -> List[Dict[str, Any]]:
        with session_scope() as session:
            rows = session.execute(
                select(ImageJobItemModel)
                .where(ImageJobItemModel.job_id == job_id)
                .order_by(ImageJobItemModel.page_index.asc())
            ).scalars().all()

            return [
                {
                    "page_index": int(item.page_index),
                    "status": item.status,
                    "image_url": item.image_url,
                    "error": item.error,
                    "updated_at": _to_iso(item.updated_at),
                }
                for item in rows
            ]

    def _to_dict(
        self,
        model: ImageJobModel,
        *,
        include_items: bool = True,
        items: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        payload = load_json(model.payload_json, {})
        result = load_json(model.result_json, {})
        data: Dict[str, Any] = {
            "id": model.id,
            "status": model.status,
            "task_id": model.task_id,
            "payload": payload if isinstance(payload, dict) else {},
            "result": result if isinstance(result, dict) else {},
            "error": model.error,
            "cancel_requested": bool(model.cancel_requested),
            "total_pages": int(model.total_pages or 0),
            "completed_pages": int(model.completed_pages or 0),
            "failed_pages": int(model.failed_pages or 0),
            "created_at": _to_iso(model.created_at),
            "started_at": _to_iso(model.started_at),
            "finished_at": _to_iso(model.finished_at),
            "updated_at": _to_iso(model.updated_at),
        }
        if include_items:
            data["items"] = items if items is not None else self.list_job_items(model.id)
        return data
