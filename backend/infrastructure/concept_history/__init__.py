"""概念历史记录基础设施适配器。"""

from .adapters import (
    ConceptHistoryStorageAdapterProtocol,
    LocalConceptHistoryStorageAdapter,
    create_concept_history_storage_adapter,
)

__all__ = [
    "ConceptHistoryStorageAdapterProtocol",
    "LocalConceptHistoryStorageAdapter",
    "create_concept_history_storage_adapter",
]
