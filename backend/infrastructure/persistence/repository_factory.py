"""数据库仓储实例工厂。"""

from __future__ import annotations

from backend.domain.ports import (
    ConceptRepositoryPort,
    HistoryRepositoryPort,
    ImageJobRepositoryPort,
    PublishRepositoryPort,
)

from .concept_repository import SqlAlchemyConceptRepository
from .history_repository import SqlAlchemyHistoryRepository
from .image_job_repository import SqlAlchemyImageJobRepository
from .publish_repository import SqlAlchemyPublishRepository

_history_repository: HistoryRepositoryPort | None = None
_concept_repository: ConceptRepositoryPort | None = None
_publish_repository: PublishRepositoryPort | None = None
_image_job_repository: ImageJobRepositoryPort | None = None


def get_history_repository() -> HistoryRepositoryPort:
    """获取历史记录数据库仓储单例。"""
    global _history_repository
    if _history_repository is None:
        _history_repository = SqlAlchemyHistoryRepository()
    return _history_repository


def get_concept_repository() -> ConceptRepositoryPort:
    """获取概念记录数据库仓储单例。"""
    global _concept_repository
    if _concept_repository is None:
        _concept_repository = SqlAlchemyConceptRepository()
    return _concept_repository


def get_publish_repository() -> PublishRepositoryPort:
    """获取发布记录数据库仓储单例。"""
    global _publish_repository
    if _publish_repository is None:
        _publish_repository = SqlAlchemyPublishRepository()
    return _publish_repository


def get_image_job_repository() -> ImageJobRepositoryPort:
    """获取图片任务数据库仓储单例。"""
    global _image_job_repository
    if _image_job_repository is None:
        _image_job_repository = SqlAlchemyImageJobRepository()
    return _image_job_repository


def reset_repository_singletons() -> None:
    """重置仓储单例（用于测试隔离）。"""
    global _history_repository, _concept_repository, _publish_repository, _image_job_repository
    _history_repository = None
    _concept_repository = None
    _publish_repository = None
    _image_job_repository = None
