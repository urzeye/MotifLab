"""内容生成应用层服务。"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from backend.infrastructure.services.content import ContentService, get_content_service

from .history_application_service import (
    HistoryApplicationService,
    get_history_application_service,
)

_content_application_service: "ContentApplicationService | None" = None
logger = logging.getLogger(__name__)


class ContentApplicationService:
    """封装内容生成与历史回写编排。"""

    def __init__(
        self,
        content_service: ContentService,
        history_service: HistoryApplicationService,
    ) -> None:
        self._content_service = content_service
        self._history_service = history_service

    def generate_content(
        self,
        topic: str,
        outline: Any,
        record_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """生成内容，并在可选情况下回写历史记录。"""
        result = self._content_service.generate_content(topic, outline)
        if not result.get("success") or not record_id:
            return result

        try:
            content_payload = {
                "titles": result.get("titles", []),
                "copywriting": result.get("copywriting", ""),
                "tags": result.get("tags", []),
            }
            updated = self._history_service.update_record(record_id, content=content_payload)
            if not updated:
                logger.warning(f"内容回写历史记录失败: record_id={record_id}")
        except Exception as history_error:
            logger.warning(f"内容回写历史记录异常（已忽略）: record_id={record_id}, error={history_error}")
        return result


def get_content_application_service() -> ContentApplicationService:
    """获取内容生成应用层服务（单例）。"""
    global _content_application_service
    if _content_application_service is None:
        _content_application_service = ContentApplicationService(
            content_service=get_content_service(),
            history_service=get_history_application_service(),
        )
    return _content_application_service
