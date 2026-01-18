"""事件/进度通知系统"""
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import asyncio
import time
import json
import threading
from queue import Queue, Empty


class EventType(Enum):
    """事件类型"""
    # 流水线事件
    PIPELINE_START = "pipeline.start"
    PIPELINE_PROGRESS = "pipeline.progress"
    PIPELINE_STEP_COMPLETE = "pipeline.step_complete"
    PIPELINE_ERROR = "pipeline.error"
    PIPELINE_FINISH = "pipeline.finish"

    # 技能事件
    SKILL_START = "skill.start"
    SKILL_PROGRESS = "skill.progress"
    SKILL_COMPLETE = "skill.complete"
    SKILL_ERROR = "skill.error"

    # 通用事件
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"


@dataclass
class Event:
    """事件对象"""
    type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: Optional[str] = None
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "source": self.source,
            "correlation_id": self.correlation_id
        }

    def to_sse(self) -> str:
        """转换为 SSE 格式"""
        nl = chr(10)
        return f"event: {self.type.value}{nl}data: {json.dumps(self.data)}{nl}{nl}"


class EventEmitter:
    """事件发射器"""

    def __init__(self):
        self._handlers: Dict[EventType, List[Callable[[Event], None]]] = defaultdict(list)
        self._async_handlers: Dict[EventType, List[Callable[[Event], Any]]] = defaultdict(list)
        self._wildcard_handlers: List[Callable[[Event], None]] = []
        self._async_wildcard_handlers: List[Callable[[Event], Any]] = []

    def on(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """注册同步事件处理器"""
        self._handlers[event_type].append(handler)

    def on_async(self, event_type: EventType, handler: Callable[[Event], Any]) -> None:
        """注册异步事件处理器"""
        self._async_handlers[event_type].append(handler)

    def on_all(self, handler: Callable[[Event], None]) -> None:
        """注册通配符处理器"""
        self._wildcard_handlers.append(handler)

    def on_all_async(self, handler: Callable[[Event], Any]) -> None:
        """注册异步通配符处理器"""
        self._async_wildcard_handlers.append(handler)

    def off(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """移除事件处理器"""
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
        if handler in self._async_handlers[event_type]:
            self._async_handlers[event_type].remove(handler)

    def emit(self, event: Event) -> None:
        """发射事件"""
        for handler in self._handlers[event.type]:
            try:
                handler(event)
            except Exception:
                pass
        for handler in self._wildcard_handlers:
            try:
                handler(event)
            except Exception:
                pass

    async def emit_async(self, event: Event) -> None:
        """异步发射事件"""
        self.emit(event)
        tasks = []
        for handler in self._async_handlers[event.type]:
            tasks.append(handler(event))
        for handler in self._async_wildcard_handlers:
            tasks.append(handler(event))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def clear(self, event_type: Optional[EventType] = None) -> None:
        """清除处理器"""
        if event_type:
            self._handlers[event_type] = []
            self._async_handlers[event_type] = []
        else:
            self._handlers.clear()
            self._async_handlers.clear()
            self._wildcard_handlers.clear()
            self._async_wildcard_handlers.clear()


class SSEChannel:
    """SSE 通道"""

    def __init__(self, channel_id: str, max_size: int = 100):
        self.channel_id = channel_id
        self.max_size = max_size
        self._queue: Queue = Queue(maxsize=max_size)
        self._subscribers: Set[str] = set()
        self._closed = False

    def publish(self, event: Event) -> bool:
        """发布事件到通道"""
        if self._closed:
            return False
        try:
            if self._queue.full():
                try:
                    self._queue.get_nowait()
                except Empty:
                    pass
            self._queue.put_nowait(event)
            return True
        except Exception:
            return False

    def subscribe(self, subscriber_id: str) -> None:
        """订阅通道"""
        self._subscribers.add(subscriber_id)

    def unsubscribe(self, subscriber_id: str) -> None:
        """取消订阅"""
        self._subscribers.discard(subscriber_id)

    def get_events(self, timeout: float = 0.1) -> List[Event]:
        """获取事件列表"""
        events = []
        try:
            while True:
                event = self._queue.get(timeout=timeout)
                events.append(event)
        except Empty:
            pass
        return events

    async def stream(self):
        """异步流式获取事件"""
        while not self._closed:
            events = self.get_events()
            for event in events:
                yield event.to_sse()
            if not events:
                await asyncio.sleep(0.1)

    def close(self) -> None:
        """关闭通道"""
        self._closed = True
        self._subscribers.clear()

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


class EventBus:
    """全局事件总线"""
    _instance: Optional["EventBus"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "EventBus":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._emitter = EventEmitter()
        self._channels: Dict[str, SSEChannel] = {}
        self._initialized = True

    @property
    def emitter(self) -> EventEmitter:
        return self._emitter

    def create_channel(self, channel_id: str, max_size: int = 100) -> SSEChannel:
        """创建 SSE 通道"""
        if channel_id not in self._channels:
            self._channels[channel_id] = SSEChannel(channel_id, max_size)
        return self._channels[channel_id]

    def get_channel(self, channel_id: str) -> Optional[SSEChannel]:
        """获取 SSE 通道"""
        return self._channels.get(channel_id)

    def close_channel(self, channel_id: str) -> None:
        """关闭并移除通道"""
        if channel_id in self._channels:
            self._channels[channel_id].close()
            del self._channels[channel_id]

    def publish(self, event: Event, channel_id: Optional[str] = None) -> None:
        """发布事件"""
        self._emitter.emit(event)
        if channel_id and channel_id in self._channels:
            self._channels[channel_id].publish(event)

    async def publish_async(self, event: Event, channel_id: Optional[str] = None) -> None:
        """异步发布事件"""
        await self._emitter.emit_async(event)
        if channel_id and channel_id in self._channels:
            self._channels[channel_id].publish(event)


def get_event_bus() -> EventBus:
    """获取全局事件总线实例"""
    return EventBus()
