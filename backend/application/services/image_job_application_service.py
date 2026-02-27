"""异步图片任务应用层服务。"""

from __future__ import annotations

import base64
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.domain.ports import ImageJobRepositoryPort
from backend.infrastructure.persistence import get_image_job_repository

from .image_generation_application_service import (
    ImageGenerationApplicationService,
    get_image_generation_application_service,
)

_image_job_application_service: "ImageJobApplicationService | None" = None


def _parse_base64_images(images_base64: Any) -> List[bytes]:
    """解析 base64 图片字符串列表。"""
    if not isinstance(images_base64, list):
        return []
    result: List[bytes] = []
    for item in images_base64:
        if not isinstance(item, str):
            continue
        encoded = item.split(",", 1)[1] if "," in item else item
        try:
            result.append(base64.b64decode(encoded))
        except Exception:
            continue
    return result


class ImageJobApplicationService:
    """负责图片任务的创建、执行、查询与取消。"""

    def __init__(
        self,
        image_generation_service: ImageGenerationApplicationService,
        repository: ImageJobRepositoryPort,
    ) -> None:
        self._image_generation_service = image_generation_service
        self._repository = repository
        max_workers = max(1, int(os.getenv("IMAGE_JOB_MAX_WORKERS", "2")))
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="image-job")
        self._futures: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def create_job(
        self,
        *,
        pages: List[Dict[str, Any]],
        task_id: Optional[str] = None,
        full_outline: str = "",
        user_images_base64: Optional[List[str]] = None,
        user_topic: str = "",
        user_prompt: str = "",
        system_prompt: str = "",
    ) -> str:
        """创建异步任务并启动后台执行。"""
        normalized_task_id = (task_id or "").strip() if isinstance(task_id, str) or task_id is None else str(task_id).strip()
        payload = {
            "pages": pages,
            "task_id": normalized_task_id or None,
            "full_outline": full_outline,
            "user_images": user_images_base64 or [],
            "user_topic": user_topic,
            "user_prompt": user_prompt,
            "system_prompt": system_prompt,
        }
        job_id = self._repository.create_job(payload, status="queued")
        for page in pages:
            index = int(page.get("index", -1))
            if index >= 0:
                self._repository.upsert_job_item(job_id, index, {"status": "queued"})

        with self._lock:
            self._futures[job_id] = self._executor.submit(self._run_job, job_id)
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取任务详情。"""
        return self._repository.get_job(job_id)

    def list_jobs(self, page: int = 1, page_size: int = 20, status: Optional[str] = None) -> Dict[str, Any]:
        """分页查询任务列表。"""
        return self._repository.list_jobs(page=page, page_size=page_size, status=status)

    def cancel_job(self, job_id: str) -> bool:
        """请求取消任务。"""
        return self._repository.mark_cancel_requested(job_id)

    def _run_job(self, job_id: str) -> None:
        """后台执行任务。"""
        job = self._repository.get_job(job_id)
        if not job:
            return

        payload = job.get("payload", {})
        pages = payload.get("pages", [])
        if not isinstance(pages, list) or not pages:
            self._repository.update_job(
                job_id,
                {
                    "status": "failed",
                    "error": "任务参数错误：pages 不能为空",
                    "finished_at": datetime.now(timezone.utc),
                },
            )
            return

        task_id = payload.get("task_id")
        if isinstance(task_id, str):
            task_id = task_id.strip() or None
        full_outline = str(payload.get("full_outline") or "")
        user_topic = str(payload.get("user_topic") or "")
        user_prompt = str(payload.get("user_prompt") or "")
        system_prompt = str(payload.get("system_prompt") or "")
        user_images = _parse_base64_images(payload.get("user_images"))

        self._repository.update_job(
            job_id,
            {
                "status": "running",
                "started_at": datetime.now(timezone.utc),
                "total_pages": len(pages),
                "completed_pages": 0,
                "failed_pages": 0,
                "error": None,
            },
        )

        generated_images: Dict[int, str] = {}
        completed_count = 0
        failed_count = 0
        final_task_id = task_id

        try:
            for event in self._image_generation_service.generate_images(
                pages=pages,
                task_id=task_id,
                full_outline=full_outline,
                user_images=user_images if user_images else None,
                user_topic=user_topic,
                user_prompt=user_prompt,
                system_prompt=system_prompt,
            ):
                latest = self._repository.get_job(job_id)
                if latest and latest.get("cancel_requested"):
                    self._repository.update_job(
                        job_id,
                        {
                            "status": "cancelled",
                            "finished_at": datetime.now(timezone.utc),
                            "result": {
                                "task_id": final_task_id,
                                "images": generated_images,
                                "completed": completed_count,
                                "failed": failed_count,
                            },
                        },
                    )
                    return

                event_type = str(event.get("event") or "")
                event_data = event.get("data") if isinstance(event.get("data"), dict) else {}
                if event_type == "complete":
                    idx = int(event_data.get("index", -1))
                    image_url = str(event_data.get("image_url") or "")
                    if idx >= 0 and image_url:
                        generated_images[idx] = image_url
                        completed_count += 1
                        self._repository.upsert_job_item(
                            job_id,
                            idx,
                            {"status": "success", "image_url": image_url, "error": None},
                        )
                        self._repository.update_job(
                            job_id,
                            {"completed_pages": completed_count, "failed_pages": failed_count},
                        )
                elif event_type == "error":
                    idx = int(event_data.get("index", -1))
                    message = str(event_data.get("message") or "生成失败")
                    if idx >= 0:
                        failed_count += 1
                        self._repository.upsert_job_item(
                            job_id,
                            idx,
                            {"status": "failed", "error": message},
                        )
                        self._repository.update_job(
                            job_id,
                            {"completed_pages": completed_count, "failed_pages": failed_count},
                        )
                elif event_type == "finish":
                    final_task_id = event_data.get("task_id") or final_task_id

            final_status = "success" if failed_count == 0 else "failed"
            self._repository.update_job(
                job_id,
                {
                    "status": final_status,
                    "task_id": final_task_id,
                    "finished_at": datetime.now(timezone.utc),
                    "result": {
                        "task_id": final_task_id,
                        "images": generated_images,
                        "completed": completed_count,
                        "failed": failed_count,
                    },
                },
            )
        except Exception as exc:
            self._repository.update_job(
                job_id,
                {
                    "status": "failed",
                    "error": str(exc),
                    "finished_at": datetime.now(timezone.utc),
                    "result": {
                        "task_id": final_task_id,
                        "images": generated_images,
                        "completed": completed_count,
                        "failed": failed_count,
                    },
                },
            )
        finally:
            with self._lock:
                self._futures.pop(job_id, None)


def get_image_job_application_service() -> ImageJobApplicationService:
    """获取异步图片任务应用层服务单例。"""
    global _image_job_application_service
    if _image_job_application_service is None:
        _image_job_application_service = ImageJobApplicationService(
            image_generation_service=get_image_generation_application_service(),
            repository=get_image_job_repository(),
        )
    return _image_job_application_service
