"""流水线应用层服务。"""

from __future__ import annotations

import base64
from typing import Any, Dict, Iterable

from backend.services.pipeline_service import PipelineService, get_pipeline_service

_pipeline_application_service: "PipelineApplicationService | None" = None


class PipelineApplicationService:
    """封装流水线执行编排与输入标准化。"""

    def __init__(self, pipeline_service: PipelineService) -> None:
        self._pipeline_service = pipeline_service

    @staticmethod
    def _normalize_input_data(input_data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化输入并处理 base64 图片字段。"""
        normalized = dict(input_data or {})
        images = normalized.get("images")
        if not isinstance(images, list):
            return normalized

        decoded_images = []
        for image in images:
            if not isinstance(image, str):
                continue
            encoded = image.split(",", 1)[1] if "," in image else image
            decoded_images.append(base64.b64decode(encoded))
        normalized["images"] = decoded_images
        return normalized

    def get_available_pipelines(self) -> Dict[str, str]:
        """获取可用流水线列表。"""
        return self._pipeline_service.get_available_pipelines()

    def run_pipeline(
        self,
        pipeline_type: str,
        input_data: Dict[str, Any],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """同步执行流水线。"""
        return self._pipeline_service.run_pipeline(
            pipeline_type=pipeline_type,
            input_data=self._normalize_input_data(input_data),
            config=config,
        )

    def run_pipeline_stream(
        self,
        pipeline_type: str,
        input_data: Dict[str, Any],
        config: Dict[str, Any],
    ) -> Iterable[Any]:
        """流式执行流水线。"""
        return self._pipeline_service.run_pipeline_stream(
            pipeline_type=pipeline_type,
            input_data=self._normalize_input_data(input_data),
            config=config,
        )

    def cancel_pipeline(self, run_id: str) -> bool:
        """取消流水线。"""
        return self._pipeline_service.cancel_pipeline(run_id)


def get_pipeline_application_service() -> PipelineApplicationService:
    """获取流水线应用层服务（单例）。"""
    global _pipeline_application_service
    if _pipeline_application_service is None:
        _pipeline_application_service = PipelineApplicationService(get_pipeline_service())
    return _pipeline_application_service
