"""图片生成应用层服务。"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from backend.infrastructure.services.image import ImageService, get_image_service

_image_generation_application_service: ImageGenerationApplicationService | None = None


class ImageGenerationApplicationService:
    """封装图片生成领域的应用层编排。"""

    def __init__(self, image_service: ImageService) -> None:
        self._image_service = image_service

    def generate_images(
        self,
        pages: list[dict[str, Any]],
        task_id: str | None = None,
        full_outline: str = "",
        user_images: list[bytes] | None = None,
        user_topic: str = "",
        user_prompt: str = "",
        system_prompt: str = "",
    ) -> Generator[dict[str, Any], None, None]:
        """发起图片生成任务并返回事件流。"""
        normalized_task_id = (task_id or "").strip()
        # 重要：空字符串必须转回 None，底层服务才会自动生成 task_id。
        resolved_task_id = normalized_task_id or None
        return self._image_service.generate_images(
            pages=pages,
            task_id=resolved_task_id,
            full_outline=full_outline,
            user_images=user_images,
            user_topic=user_topic,
            custom_prompt=user_prompt,
            system_prompt=system_prompt,
        )

    def retry_single_image(
        self,
        task_id: str,
        page: dict[str, Any],
        use_reference: bool = True,
        full_outline: str = "",
        user_topic: str = "",
        user_prompt: str = "",
        system_prompt: str = "",
    ) -> dict[str, Any]:
        """重试单张图片生成。"""
        return self._image_service.retry_single_image(
            task_id=task_id,
            page=page,
            use_reference=use_reference,
            full_outline=full_outline,
            user_topic=user_topic,
            custom_prompt=user_prompt,
            system_prompt=system_prompt,
        )

    def retry_failed_images(
        self,
        task_id: str,
        pages: list[dict[str, Any]],
        user_prompt: str = "",
        system_prompt: str = "",
    ) -> Generator[dict[str, Any], None, None]:
        """批量重试失败图片。"""
        return self._image_service.retry_failed_images(
            task_id=task_id,
            pages=pages,
            custom_prompt=user_prompt,
            system_prompt=system_prompt,
        )

    def regenerate_image(
        self,
        task_id: str,
        page: dict[str, Any],
        use_reference: bool = True,
        full_outline: str = "",
        user_topic: str = "",
        user_prompt: str = "",
        system_prompt: str = "",
    ) -> dict[str, Any]:
        """重新生成单张图片。"""
        return self._image_service.regenerate_image(
            task_id=task_id,
            page=page,
            use_reference=use_reference,
            full_outline=full_outline,
            user_topic=user_topic,
            custom_prompt=user_prompt,
            system_prompt=system_prompt,
        )

    def get_task_state(self, task_id: str) -> dict[str, Any] | None:
        """获取图片任务状态。"""
        return self._image_service.get_task_state(task_id)

    def reset_runtime_cache(self) -> None:
        """重置图片生成运行时单例缓存。"""
        from backend.infrastructure.services.image import reset_image_service

        reset_image_service()


def get_image_generation_application_service() -> ImageGenerationApplicationService:
    """获取图片生成应用层服务（单例）。"""
    global _image_generation_application_service
    if _image_generation_application_service is None:
        _image_generation_application_service = ImageGenerationApplicationService(get_image_service())
    return _image_generation_application_service
