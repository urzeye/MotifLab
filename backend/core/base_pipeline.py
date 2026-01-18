"""流水线抽象基类模块"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, List, Optional, Callable, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import time
import uuid

from .base_skill import BaseSkill, SkillResult, SkillStatus


class PipelineStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PipelineEvent:
    """流水线事件"""
    event: str
    step: Optional[int] = None
    skill: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: Optional[float] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = {"event": self.event, "timestamp": self.timestamp}
        if self.step is not None:
            data["step"] = self.step
        if self.skill:
            data["skill"] = self.skill
        if self.result is not None:
            data["result"] = self.result
        if self.error:
            data["error"] = self.error
        if self.progress is not None:
            data["progress"] = self.progress
        if self.metadata:
            data["metadata"] = self.metadata
        return data


@dataclass
class PipelineContext:
    """流水线执行上下文"""
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    variables: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, SkillResult] = field(default_factory=dict)
    current_step: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    def get(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.variables[key] = value

    @property
    def elapsed_time(self) -> Optional[float]:
        if self.start_time is None:
            return None
        end = self.end_time or time.time()
        return end - self.start_time


class BasePipeline(ABC):
    """流水线抽象基类"""
    name: str = "base_pipeline"
    description: str = ""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.skills: List[BaseSkill] = self.build_skills()
        self._status = PipelineStatus.IDLE
        self._context: Optional[PipelineContext] = None
        self._event_handlers: List[Callable[[PipelineEvent], None]] = []

    @abstractmethod
    def build_skills(self) -> List[BaseSkill]:
        """构建技能列表"""
        pass

    @property
    def status(self) -> PipelineStatus:
        return self._status

    @property
    def context(self) -> Optional[PipelineContext]:
        return self._context

    def add_event_handler(self, handler: Callable[[PipelineEvent], None]) -> None:
        self._event_handlers.append(handler)

    def remove_event_handler(self, handler: Callable[[PipelineEvent], None]) -> None:
        if handler in self._event_handlers:
            self._event_handlers.remove(handler)

    def _emit_event(self, event: PipelineEvent) -> None:
        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception:
                pass

    def run_stream(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> Generator[PipelineEvent, None, None]:
        """流式执行流水线，支持 SSE"""
        self._context = PipelineContext()
        if context:
            self._context.variables.update(context)
        self._context.start_time = time.time()
        self._status = PipelineStatus.RUNNING
        total_skills = len(self.skills)
        current_data = input_data

        start_event = PipelineEvent(event="start", metadata={"pipeline": self.name, "total_steps": total_skills, "run_id": self._context.run_id})
        self._emit_event(start_event)
        yield start_event

        try:
            for i, skill in enumerate(self.skills):
                step = i + 1
                self._context.current_step = step
                progress = step / total_skills

                progress_event = PipelineEvent(event="progress", step=step, skill=skill.name, progress=progress, metadata={"status": "running"})
                self._emit_event(progress_event)
                yield progress_event

                skill_context = {"pipeline": self.name, "step": step, "run_id": self._context.run_id, **self._context.variables}
                result = skill.execute(current_data, skill_context)
                self._context.results[skill.name] = result

                if not result.success:
                    error_event = PipelineEvent(event="error", step=step, skill=skill.name, error=result.error, metadata={"status": "failed"})
                    self._emit_event(error_event)
                    yield error_event
                    self._status = PipelineStatus.FAILED
                    self._context.end_time = time.time()
                    finish_event = PipelineEvent(event="finish", result={"success": False, "error": result.error}, metadata={"failed_at_step": step, "elapsed_time": self._context.elapsed_time})
                    self._emit_event(finish_event)
                    yield finish_event
                    return

                complete_event = PipelineEvent(event="step_complete", step=step, skill=skill.name, result=result.to_dict(), progress=progress, metadata={"status": "completed"})
                self._emit_event(complete_event)
                yield complete_event
                current_data = result.data

            self._status = PipelineStatus.SUCCESS
            self._context.end_time = time.time()
            finish_event = PipelineEvent(event="finish", result={"success": True, "data": current_data}, metadata={"elapsed_time": self._context.elapsed_time, "total_steps": total_skills})
            self._emit_event(finish_event)
            yield finish_event

        except Exception as e:
            self._status = PipelineStatus.FAILED
            self._context.end_time = time.time()
            error_event = PipelineEvent(event="error", step=self._context.current_step, error=str(e), metadata={"exception_type": type(e).__name__, "pipeline": self.name})
            self._emit_event(error_event)
            yield error_event
            finish_event = PipelineEvent(event="finish", result={"success": False, "error": str(e)}, metadata={"elapsed_time": self._context.elapsed_time})
            self._emit_event(finish_event)
            yield finish_event

    def run(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """同步执行流水线"""
        events = []
        final_result = None
        for event in self.run_stream(input_data, context):
            events.append(event.to_dict())
            if event.event == "finish":
                final_result = event.result
        return {
            "success": final_result.get("success", False) if final_result else False,
            "data": final_result.get("data") if final_result else None,
            "error": final_result.get("error") if final_result else None,
            "events": events,
            "run_id": self._context.run_id if self._context else None,
            "elapsed_time": self._context.elapsed_time if self._context else None
        }

    async def run_stream_async(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> AsyncGenerator[PipelineEvent, None]:
        """异步流式执行流水线"""
        self._context = PipelineContext()
        if context:
            self._context.variables.update(context)
        self._context.start_time = time.time()
        self._status = PipelineStatus.RUNNING
        total_skills = len(self.skills)
        current_data = input_data

        yield PipelineEvent(event="start", metadata={"pipeline": self.name, "total_steps": total_skills, "run_id": self._context.run_id})

        try:
            for i, skill in enumerate(self.skills):
                step = i + 1
                self._context.current_step = step
                progress = step / total_skills
                yield PipelineEvent(event="progress", step=step, skill=skill.name, progress=progress)

                skill_context = {"pipeline": self.name, "step": step, "run_id": self._context.run_id, **self._context.variables}
                result = await skill.run_async(current_data, skill_context)
                self._context.results[skill.name] = result

                if not result.success:
                    self._status = PipelineStatus.FAILED
                    self._context.end_time = time.time()
                    yield PipelineEvent(event="error", step=step, skill=skill.name, error=result.error)
                    yield PipelineEvent(event="finish", result={"success": False, "error": result.error})
                    return

                yield PipelineEvent(event="step_complete", step=step, skill=skill.name, result=result.to_dict(), progress=progress)
                current_data = result.data

            self._status = PipelineStatus.SUCCESS
            self._context.end_time = time.time()
            yield PipelineEvent(event="finish", result={"success": True, "data": current_data}, metadata={"elapsed_time": self._context.elapsed_time})

        except Exception as e:
            self._status = PipelineStatus.FAILED
            self._context.end_time = time.time()
            yield PipelineEvent(event="error", error=str(e), metadata={"exception_type": type(e).__name__})
            yield PipelineEvent(event="finish", result={"success": False, "error": str(e)})

    def cancel(self) -> bool:
        if self._status == PipelineStatus.RUNNING:
            self._status = PipelineStatus.CANCELLED
            return True
        return False

    def get_skill(self, name: str) -> Optional[BaseSkill]:
        for skill in self.skills:
            if skill.name == name:
                return skill
        return None

    def __repr__(self) -> str:
        skill_names = [s.name for s in self.skills]
        return f"<{self.__class__.__name__}(name={self.name}, skills={skill_names})>"
