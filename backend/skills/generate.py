"""
图像生成技能

通用的图像生成技能，支持多种图像生成服务商。
可用于小红书图文、概念图等多种场景。
"""

import logging
import os
import uuid
import time
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.core.base_skill import BaseSkill, SkillResult
from backend.clients.factory import ClientFactory
from backend.utils.image_compressor import compress_image

logger = logging.getLogger(__name__)

# 存储模式常量
STORAGE_MODE_LOCAL = "local"
STORAGE_MODE_SUPABASE = "supabase"


@dataclass
class ImagePage:
    """图像页面数据"""
    index: int
    type: str  # 'cover', 'content', 'summary'
    content: str


@dataclass
class GenerateImageInput:
    """图像生成输入"""
    pages: List[Dict[str, Any]]
    task_id: Optional[str] = None
    full_outline: str = ""
    user_images: Optional[List[bytes]] = None
    user_topic: str = ""


class GenerateImageSkill(BaseSkill):
    """
    图像生成技能

    支持流式生成（SSE）和批量生成模式。
    支持本地存储和 Supabase 云存储。
    """

    name = "generate_image"
    description = "生成图像"
    version = "2.0.0"

    # 并发配置
    MAX_CONCURRENT = 1  # 最大并发数
    REQUEST_DELAY = 35  # 请求间隔（秒）

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._client = None
        self._prompt_template = None
        self._prompt_template_short = None

        # 存储模式
        self.storage_mode = os.getenv("HISTORY_STORAGE_MODE", STORAGE_MODE_LOCAL)

        # 任务状态
        self._task_states: Dict[str, Dict] = {}

        # 历史记录目录
        self.history_root_dir = Path(__file__).parent.parent.parent / "history"
        if self.storage_mode == STORAGE_MODE_LOCAL:
            self.history_root_dir.mkdir(exist_ok=True)

        # 当前任务
        self.current_task_id = None
        self.current_task_dir = None

    @property
    def is_supabase_mode(self) -> bool:
        """是否使用 Supabase 存储"""
        return self.storage_mode == STORAGE_MODE_SUPABASE

    @property
    def client(self):
        """延迟加载图像生成客户端"""
        if self._client is None:
            provider_config = self.config.get('image_provider', {})
            if not provider_config:
                from backend.config import Config
                provider_name = Config.get_active_image_provider()
                provider_config = Config.get_image_provider_config(provider_name)
            self._client = ClientFactory.create_image_client(provider_config)
        return self._client

    @property
    def provider_config(self) -> Dict[str, Any]:
        """获取服务商配置"""
        config = self.config.get('image_provider', {})
        if not config:
            from backend.config import Config
            provider_name = Config.get_active_image_provider()
            config = Config.get_image_provider_config(provider_name)
        return config

    @property
    def use_short_prompt(self) -> bool:
        """是否使用短提示词"""
        return self.provider_config.get('short_prompt', False)

    def _load_prompt_template(self, short: bool = False) -> str:
        """加载提示词模板"""
        filename = "image_prompt_short.txt" if short else "image_prompt.txt"
        prompt_path = Path(__file__).parent.parent / "prompts" / filename
        if prompt_path.exists():
            return prompt_path.read_text(encoding='utf-8')
        return ""

    @property
    def prompt_template(self) -> str:
        if self._prompt_template is None:
            self._prompt_template = self._load_prompt_template(short=False)
        return self._prompt_template

    @property
    def prompt_template_short(self) -> str:
        if self._prompt_template_short is None:
            self._prompt_template_short = self._load_prompt_template(short=True)
        return self._prompt_template_short

    def _save_image(self, image_data: bytes, filename: str) -> str:
        """保存图片"""
        if self.is_supabase_mode:
            return self._save_image_supabase(image_data, filename)
        return self._save_image_local(image_data, filename)

    def _save_image_supabase(self, image_data: bytes, filename: str) -> str:
        """Supabase 模式保存"""
        from backend.utils.supabase_client import upload_image

        if self.current_task_id is None:
            raise ValueError("任务 ID 未设置")

        url = upload_image(self.current_task_id, filename, image_data)
        if not url:
            raise Exception(f"上传图片失败: {filename}")

        # 上传缩略图
        thumbnail_data = compress_image(image_data, max_size_kb=50)
        upload_image(self.current_task_id, f"thumb_{filename}", thumbnail_data)

        return url

    def _save_image_local(self, image_data: bytes, filename: str) -> str:
        """本地模式保存"""
        if self.current_task_dir is None:
            raise ValueError("任务目录未设置")

        filepath = self.current_task_dir / filename
        filepath.write_bytes(image_data)

        # 保存缩略图
        thumbnail_data = compress_image(image_data, max_size_kb=50)
        (self.current_task_dir / f"thumb_{filename}").write_bytes(thumbnail_data)

        return str(filepath)

    def _generate_single_image(
        self,
        page: Dict,
        reference_image: Optional[bytes] = None,
        full_outline: str = "",
        user_images: Optional[List[bytes]] = None,
        user_topic: str = ""
    ) -> Tuple[int, bool, Optional[str], Optional[str], Optional[bytes]]:
        """
        生成单张图片

        Returns:
            (index, success, filename, error_message, image_bytes)
        """
        index = page["index"]
        page_type = page["type"]
        page_content = page["content"]

        try:
            logger.debug(f"生成图片 [{index}]: type={page_type}")

            # 构建提示词
            if self.use_short_prompt and self.prompt_template_short:
                prompt = self.prompt_template_short.format(
                    page_content=page_content,
                    page_type=page_type
                )
            else:
                prompt = self.prompt_template.format(
                    page_content=page_content,
                    page_type=page_type,
                    full_outline=full_outline,
                    user_topic=user_topic or "未提供"
                )

            # 根据服务商类型调用生成器
            provider_type = self.provider_config.get('type', '')

            if provider_type == 'google_genai':
                image_data = self.client.generate_image(
                    prompt=prompt,
                    aspect_ratio=self.provider_config.get('default_aspect_ratio', '3:4'),
                    temperature=self.provider_config.get('temperature', 1.0),
                    model=self.provider_config.get('model', 'gemini-3-pro-image-preview'),
                    reference_image=reference_image,
                )
            elif provider_type == 'image_api':
                reference_images = []
                if user_images:
                    reference_images.extend(user_images)
                if reference_image:
                    reference_images.append(reference_image)

                image_data = self.client.generate_image(
                    prompt=prompt,
                    aspect_ratio=self.provider_config.get('default_aspect_ratio', '3:4'),
                    temperature=self.provider_config.get('temperature', 1.0),
                    model=self.provider_config.get('model', 'nano-banana-2'),
                    reference_images=reference_images if reference_images else None,
                )
            else:
                # OpenAI 兼容模式
                image_data = self.client.generate_image(
                    prompt=prompt,
                    size=self.provider_config.get('default_size', '1024x1024'),
                    model=self.provider_config.get('model'),
                    quality=self.provider_config.get('quality', 'standard'),
                )

            # 保存图片
            filename = f"{index}.png"
            self._save_image(image_data, filename)
            logger.info(f"✅ 图片 [{index}] 生成成功: {filename}")

            return (index, True, filename, None, image_data)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ 图片 [{index}] 生成失败: {error_msg[:200]}")
            return (index, False, None, error_msg, None)

    def get_required_inputs(self) -> List[str]:
        return ['pages']

    def get_output_schema(self) -> Dict[str, Any]:
        return {
            'type': 'object',
            'properties': {
                'task_id': {'type': 'string'},
                'images': {'type': 'array', 'items': {'type': 'string'}},
                'total': {'type': 'integer'},
                'completed': {'type': 'integer'},
                'failed': {'type': 'integer'}
            }
        }

    def run(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> SkillResult:
        """
        同步执行图像生成（生成所有图片后返回）

        对于流式生成，请使用 run_stream() 方法。
        """
        # 收集所有结果
        results = list(self.run_stream(input_data, context))

        # 找到最终结果
        final_result = None
        for r in results:
            if r.get('event') == 'finish':
                final_result = r.get('data', {})
                break

        if final_result:
            return SkillResult(
                success=final_result.get('success', False),
                data=final_result,
                metadata={'skill': self.name}
            )
        else:
            return SkillResult(
                success=False,
                error="图像生成过程异常终止",
                metadata={'skill': self.name}
            )

    def run_stream(
        self,
        input_data: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        流式执行图像生成（支持 SSE）

        Yields:
            进度事件字典
        """
        context = context or {}

        # 解析输入
        if isinstance(input_data, GenerateImageInput):
            pages = input_data.pages
            task_id = input_data.task_id
            full_outline = input_data.full_outline
            user_images = input_data.user_images
            user_topic = input_data.user_topic
        elif isinstance(input_data, dict):
            pages = input_data.get('pages', [])
            task_id = input_data.get('task_id')
            full_outline = input_data.get('full_outline', '')
            user_images = input_data.get('user_images')
            user_topic = input_data.get('user_topic', '')
        else:
            yield {
                "event": "error",
                "data": {"message": "输入格式错误"}
            }
            return

        if not pages:
            yield {
                "event": "error",
                "data": {"message": "页面列表为空"}
            }
            return

        # 设置任务
        if task_id is None:
            task_id = f"task_{uuid.uuid4().hex[:8]}"

        self.current_task_id = task_id
        if self.is_supabase_mode:
            self.current_task_dir = None
        else:
            self.current_task_dir = self.history_root_dir / task_id
            self.current_task_dir.mkdir(exist_ok=True)

        logger.info(f"开始图片生成任务: task_id={task_id}, pages={len(pages)}")

        total = len(pages)
        generated_images = []
        failed_pages = []
        cover_image_data = None

        # 压缩用户参考图
        compressed_user_images = None
        if user_images:
            compressed_user_images = [compress_image(img, max_size_kb=200) for img in user_images]

        # 初始化任务状态
        self._task_states[task_id] = {
            "pages": pages,
            "generated": {},
            "failed": {},
            "cover_image": None,
            "full_outline": full_outline,
            "user_images": compressed_user_images,
            "user_topic": user_topic
        }

        # ===== 第一阶段：生成封面 =====
        cover_page = None
        other_pages = []

        for page in pages:
            if page["type"] == "cover":
                cover_page = page
            else:
                other_pages.append(page)

        if cover_page is None and len(pages) > 0:
            cover_page = pages[0]
            other_pages = pages[1:]

        if cover_page:
            yield {
                "event": "progress",
                "data": {
                    "index": cover_page["index"],
                    "status": "generating",
                    "message": "正在生成封面...",
                    "current": 1,
                    "total": total,
                    "phase": "cover"
                }
            }

            index, success, filename, error, cover_bytes = self._generate_single_image(
                cover_page,
                reference_image=None,
                full_outline=full_outline,
                user_images=compressed_user_images,
                user_topic=user_topic
            )

            if success:
                generated_images.append(filename)
                self._task_states[task_id]["generated"][index] = filename

                if cover_bytes:
                    cover_image_data = compress_image(cover_bytes, max_size_kb=200)
                    self._task_states[task_id]["cover_image"] = cover_image_data

                yield {
                    "event": "complete",
                    "data": {
                        "index": index,
                        "status": "done",
                        "image_url": f"/api/images/{task_id}/{filename}",
                        "phase": "cover"
                    }
                }

                # 等待避免速率限制
                if self.REQUEST_DELAY > 0 and other_pages:
                    yield {
                        "event": "progress",
                        "data": {
                            "status": "waiting",
                            "message": f"等待 {self.REQUEST_DELAY} 秒...",
                            "current": 1,
                            "total": total,
                            "phase": "cover"
                        }
                    }
                    time.sleep(self.REQUEST_DELAY)
            else:
                failed_pages.append(cover_page)
                self._task_states[task_id]["failed"][index] = error
                yield {
                    "event": "error",
                    "data": {
                        "index": index,
                        "status": "error",
                        "message": error,
                        "retryable": True,
                        "phase": "cover"
                    }
                }

        # ===== 第二阶段：生成其他页面 =====
        if other_pages:
            high_concurrency = self.provider_config.get('high_concurrency', False)

            yield {
                "event": "progress",
                "data": {
                    "status": "batch_start",
                    "message": f"开始生成 {len(other_pages)} 页内容...",
                    "current": len(generated_images),
                    "total": total,
                    "phase": "content"
                }
            }

            if high_concurrency:
                # 并发模式
                with ThreadPoolExecutor(max_workers=self.MAX_CONCURRENT) as executor:
                    future_to_page = {
                        executor.submit(
                            self._generate_single_image,
                            page,
                            cover_image_data,
                            full_outline,
                            compressed_user_images,
                            user_topic
                        ): page
                        for page in other_pages
                    }

                    for future in as_completed(future_to_page):
                        page = future_to_page[future]
                        try:
                            index, success, filename, error, _ = future.result()
                            if success:
                                generated_images.append(filename)
                                self._task_states[task_id]["generated"][index] = filename
                                yield {
                                    "event": "complete",
                                    "data": {
                                        "index": index,
                                        "status": "done",
                                        "image_url": f"/api/images/{task_id}/{filename}",
                                        "phase": "content"
                                    }
                                }
                            else:
                                failed_pages.append(page)
                                self._task_states[task_id]["failed"][index] = error
                                yield {
                                    "event": "error",
                                    "data": {
                                        "index": index,
                                        "status": "error",
                                        "message": error,
                                        "retryable": True,
                                        "phase": "content"
                                    }
                                }
                        except Exception as e:
                            failed_pages.append(page)
                            yield {
                                "event": "error",
                                "data": {
                                    "index": page["index"],
                                    "status": "error",
                                    "message": str(e),
                                    "retryable": True,
                                    "phase": "content"
                                }
                            }
            else:
                # 顺序模式
                for i, page in enumerate(other_pages):
                    if i > 0 and self.REQUEST_DELAY > 0:
                        yield {
                            "event": "progress",
                            "data": {
                                "index": page["index"],
                                "status": "waiting",
                                "message": f"等待 {self.REQUEST_DELAY} 秒...",
                                "current": len(generated_images),
                                "total": total,
                                "phase": "content"
                            }
                        }
                        time.sleep(self.REQUEST_DELAY)

                    yield {
                        "event": "progress",
                        "data": {
                            "index": page["index"],
                            "status": "generating",
                            "current": len(generated_images) + 1,
                            "total": total,
                            "phase": "content"
                        }
                    }

                    index, success, filename, error, _ = self._generate_single_image(
                        page,
                        cover_image_data,
                        full_outline,
                        compressed_user_images,
                        user_topic
                    )

                    if success:
                        generated_images.append(filename)
                        self._task_states[task_id]["generated"][index] = filename
                        yield {
                            "event": "complete",
                            "data": {
                                "index": index,
                                "status": "done",
                                "image_url": f"/api/images/{task_id}/{filename}",
                                "phase": "content"
                            }
                        }
                    else:
                        failed_pages.append(page)
                        self._task_states[task_id]["failed"][index] = error
                        yield {
                            "event": "error",
                            "data": {
                                "index": index,
                                "status": "error",
                                "message": error,
                                "retryable": True,
                                "phase": "content"
                            }
                        }

        # ===== 完成 =====
        yield {
            "event": "finish",
            "data": {
                "success": len(failed_pages) == 0,
                "task_id": task_id,
                "images": generated_images,
                "total": total,
                "completed": len(generated_images),
                "failed": len(failed_pages),
                "failed_indices": [p["index"] for p in failed_pages]
            }
        }

    def retry_single_image(
        self,
        task_id: str,
        page: Dict,
        use_reference: bool = True,
        full_outline: str = "",
        user_topic: str = ""
    ) -> Dict[str, Any]:
        """重试单张图片"""
        self.current_task_id = task_id
        if self.is_supabase_mode:
            self.current_task_dir = None
        else:
            self.current_task_dir = self.history_root_dir / task_id
            self.current_task_dir.mkdir(exist_ok=True)

        reference_image = None
        user_images = None

        if task_id in self._task_states:
            task_state = self._task_states[task_id]
            if use_reference:
                reference_image = task_state.get("cover_image")
            if not full_outline:
                full_outline = task_state.get("full_outline", "")
            if not user_topic:
                user_topic = task_state.get("user_topic", "")
            user_images = task_state.get("user_images")

        index, success, filename, error, _ = self._generate_single_image(
            page, reference_image, full_outline, user_images, user_topic
        )

        if success:
            if task_id in self._task_states:
                self._task_states[task_id]["generated"][index] = filename
                if index in self._task_states[task_id]["failed"]:
                    del self._task_states[task_id]["failed"][index]
            return {
                "success": True,
                "index": index,
                "image_url": f"/api/images/{task_id}/{filename}"
            }
        else:
            return {
                "success": False,
                "index": index,
                "error": error,
                "retryable": True
            }

    def get_task_state(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        return self._task_states.get(task_id)

    def cleanup_task(self, task_id: str):
        """清理任务状态"""
        if task_id in self._task_states:
            del self._task_states[task_id]
