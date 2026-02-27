"""图片生成应用层服务。"""

from __future__ import annotations

from typing import Any, Dict, Generator, List, Optional

from backend.infrastructure.services.image import ImageService, get_image_service

_image_generation_application_service: "ImageGenerationApplicationService | None" = None


class ImageGenerationApplicationService:
    """封装图片生成领域的应用层编排。"""

    def __init__(self, image_service: ImageService) -> None:
        self._image_service = image_service

    def generate_images(
        self,
        pages: list,
        task_id: Optional[str] = None,
        full_outline: str = "",
        user_images: Optional[List[bytes]] = None,
        user_topic: str = "",
        user_prompt: str = "",
        system_prompt: str = "",
    ) -> Generator[Dict[str, Any], None, None]:
        """发起图片生成任务并返回事件流。"""
        return self._image_service.generate_images(
            pages=pages,
            task_id=task_id,
            full_outline=full_outline,
            user_images=user_images,
            user_topic=user_topic,
            custom_prompt=user_prompt,
            system_prompt=system_prompt,
        )

    def retry_single_image(
        self,
        task_id: str,
        page: Dict[str, Any],
        use_reference: bool = True,
        full_outline: str = "",
        user_topic: str = "",
        user_prompt: str = "",
        system_prompt: str = "",
    ) -> Dict[str, Any]:
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
        pages: List[Dict[str, Any]],
        user_prompt: str = "",
        system_prompt: str = "",
    ) -> Generator[Dict[str, Any], None, None]:
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
        page: Dict[str, Any],
        use_reference: bool = True,
        full_outline: str = "",
        user_topic: str = "",
        user_prompt: str = "",
        system_prompt: str = "",
    ) -> Dict[str, Any]:
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

    def get_task_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取图片任务状态。"""
        return self._image_service.get_task_state(task_id)


def get_image_generation_application_service() -> ImageGenerationApplicationService:
    """获取图片生成应用层服务（单例）。"""
    global _image_generation_application_service
    if _image_generation_application_service is None:
        _image_generation_application_service = ImageGenerationApplicationService(get_image_service())
    return _image_generation_application_service
