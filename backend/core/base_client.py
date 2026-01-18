"""API 客户端抽象基类模块"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum


class ClientStatus(Enum):
    IDLE = "idle"
    CONNECTING = "connecting"
    READY = "ready"
    ERROR = "error"


@dataclass
class ClientResponse:
    """客户端响应"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    latency_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "usage": self.usage,
            "latency_ms": self.latency_ms,
            "metadata": self.metadata
        }


class BaseClient(ABC):
    """API 客户端抽象基类"""
    name: str = "base_client"
    provider: str = ""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._status = ClientStatus.IDLE
        self._validate_config()

    def _validate_config(self) -> None:
        pass

    @property
    def status(self) -> ClientStatus:
        return self._status

    @abstractmethod
    def connect(self) -> bool:
        """建立连接"""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """断开连接"""
        pass

    def is_ready(self) -> bool:
        return self._status == ClientStatus.READY


class BaseTextClient(BaseClient):
    """文本生成客户端抽象基类"""
    name: str = "base_text_client"

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> ClientResponse:
        """同步生成文本"""
        pass

    @abstractmethod
    async def generate_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> ClientResponse:
        """异步生成文本"""
        pass

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式生成文本"""
        result = await self.generate_async(prompt, system_prompt, temperature, max_tokens, **kwargs)
        if result.success and result.data:
            yield result.data

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> ClientResponse:
        """对话式生成"""
        lines = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            lines.append(f"{role}: {content}")
        prompt = chr(10).join(lines)
        return self.generate(prompt, temperature=temperature, max_tokens=max_tokens, **kwargs)

    async def chat_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> ClientResponse:
        """异步对话式生成"""
        lines = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            lines.append(f"{role}: {content}")
        prompt = chr(10).join(lines)
        return await self.generate_async(prompt, temperature=temperature, max_tokens=max_tokens, **kwargs)


class BaseImageClient(BaseClient):
    """图像生成客户端抽象基类"""
    name: str = "base_image_client"

    @abstractmethod
    def generate(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        num_images: int = 1,
        **kwargs
    ) -> ClientResponse:
        """同步生成图像"""
        pass

    @abstractmethod
    async def generate_async(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        num_images: int = 1,
        **kwargs
    ) -> ClientResponse:
        """异步生成图像"""
        pass

    def edit(
        self,
        image: bytes,
        prompt: str,
        mask: Optional[bytes] = None,
        **kwargs
    ) -> ClientResponse:
        """编辑图像（可选实现）"""
        return ClientResponse(success=False, error="Edit not supported by this client")

    async def edit_async(
        self,
        image: bytes,
        prompt: str,
        mask: Optional[bytes] = None,
        **kwargs
    ) -> ClientResponse:
        """异步编辑图像（可选实现）"""
        return ClientResponse(success=False, error="Edit not supported by this client")

    def upscale(
        self,
        image: bytes,
        scale: float = 2.0,
        **kwargs
    ) -> ClientResponse:
        """放大图像（可选实现）"""
        return ClientResponse(success=False, error="Upscale not supported by this client")

    async def upscale_async(
        self,
        image: bytes,
        scale: float = 2.0,
        **kwargs
    ) -> ClientResponse:
        """异步放大图像（可选实现）"""
        return ClientResponse(success=False, error="Upscale not supported by this client")
