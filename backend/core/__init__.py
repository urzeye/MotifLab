"""核心抽象层模块

导出所有核心类供外部使用。
"""

from .base_skill import (
    BaseSkill,
    SkillResult,
    SkillStatus,
)

from .base_pipeline import (
    BasePipeline,
    PipelineEvent,
    PipelineContext,
    PipelineStatus,
)

from .base_client import (
    BaseClient,
    BaseTextClient,
    BaseImageClient,
    ClientResponse,
    ClientStatus,
)

from .events import (
    Event,
    EventType,
    EventEmitter,
    EventBus,
    SSEChannel,
    get_event_bus,
)

__all__ = [
    # Skill
    "BaseSkill",
    "SkillResult",
    "SkillStatus",
    # Pipeline
    "BasePipeline",
    "PipelineEvent",
    "PipelineContext",
    "PipelineStatus",
    # Client
    "BaseClient",
    "BaseTextClient",
    "BaseImageClient",
    "ClientResponse",
    "ClientStatus",
    # Events
    "Event",
    "EventType",
    "EventEmitter",
    "EventBus",
    "SSEChannel",
    "get_event_bus",
]
