"""历史记录基础设施适配器。"""

from .adapters import (
    HistoryStorageAdapterProtocol,
    LocalHistoryStorageAdapter,
    SupabaseHistoryStorageAdapter,
    create_history_storage_adapter,
)

__all__ = [
    "HistoryStorageAdapterProtocol",
    "LocalHistoryStorageAdapter",
    "SupabaseHistoryStorageAdapter",
    "create_history_storage_adapter",
]
