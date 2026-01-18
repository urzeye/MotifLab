"""技能抽象基类模块"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

class SkillStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class SkillResult:
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> Dict[str, Any]:
        return {"success": self.success, "data": self.data, "error": self.error, "metadata": self.metadata}

class BaseSkill(ABC):
    name: str = "base_skill"
    description: str = ""
    version: str = "1.0.0"
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._status = SkillStatus.PENDING
        self._validate_config()
    def _validate_config(self) -> None:
        pass
    @property
    def status(self) -> SkillStatus:
        return self._status
    @abstractmethod
    def run(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> SkillResult:
        pass
    async def run_async(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> SkillResult:
        return self.run(input_data, context)
    def pre_run(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> Any:
        return input_data
    def post_run(self, result: SkillResult, context: Optional[Dict[str, Any]] = None) -> SkillResult:
        return result
    def execute(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> SkillResult:
        self._status = SkillStatus.RUNNING
        try:
            processed_input = self.pre_run(input_data, context)
            result = self.run(processed_input, context)
            final_result = self.post_run(result, context)
            self._status = SkillStatus.SUCCESS if final_result.success else SkillStatus.FAILED
            return final_result
        except Exception as e:
            self._status = SkillStatus.FAILED
            return SkillResult(success=False, error=str(e), metadata={"skill": self.name})
    def get_required_inputs(self) -> List[str]:
        return []
    def get_output_schema(self) -> Dict[str, Any]:
        return {}
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, version={self.version})>"
