"""
小红书图文生成流水线

流程：主题 → OutlineSkill → ContentSkill → GenerateImageSkill → 完整图文
"""

import logging
from typing import Any, Dict, Generator, List, Optional

from backend.core.base_pipeline import BasePipeline, PipelineEvent
from backend.core.base_skill import BaseSkill, SkillResult
from backend.skills.redbook import OutlineSkill, ContentSkill
from backend.skills.generate import GenerateImageSkill

logger = logging.getLogger(__name__)


class RedBookPipeline(BasePipeline):
    """
    小红书图文生成流水线

    输入：
    {
        "topic": "主题文字",
        "images": [bytes, ...],  # 可选，参考图片
        "config": {              # 可选配置
            "skip_content": bool,  # 跳过内容生成
            "skip_images": bool,   # 跳过图片生成
        }
    }

    输出：
    {
        "outline": "大纲文本",
        "pages": [...],
        "titles": [...],
        "copywriting": "...",
        "tags": [...],
        "images": [...],
        "task_id": "..."
    }
    """

    name = "redbook"
    description = "小红书图文生成流水线"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._accumulated_data: Dict[str, Any] = {}

    def build_skills(self) -> List[BaseSkill]:
        """构建技能列表"""
        text_config = self.config.get('text_provider', {})
        image_config = self.config.get('image_provider', {})

        return [
            OutlineSkill(config={'text_provider': text_config}),
            ContentSkill(config={'text_provider': text_config}),
            GenerateImageSkill(config={'image_provider': image_config}),
        ]

    def _should_skip_skill(self, skill_name: str) -> bool:
        """检查是否应跳过某个技能"""
        pipeline_config = self.config.get('pipeline', {})
        if skill_name == 'content' and pipeline_config.get('skip_content'):
            return True
        if skill_name == 'generate_image' and pipeline_config.get('skip_images'):
            return True
        return False

    def run_stream(
        self,
        input_data: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> Generator[PipelineEvent, None, None]:
        """
        流式执行小红书图文生成流水线

        特殊处理：
        1. 在技能之间传递和累积数据
        2. 图片生成技能使用其特有的 run_stream 方法
        """
        import time
        import uuid
        from backend.core.base_pipeline import PipelineContext, PipelineStatus

        # 初始化上下文
        self._context = PipelineContext()
        if context:
            self._context.variables.update(context)
        self._context.start_time = time.time()
        self._status = PipelineStatus.RUNNING

        # 解析输入
        if isinstance(input_data, dict):
            topic = input_data.get('topic', '')
            images = input_data.get('images')
            task_id = input_data.get('task_id', f"task_{uuid.uuid4().hex[:8]}")
        else:
            topic = str(input_data)
            images = None
            task_id = f"task_{uuid.uuid4().hex[:8]}"

        # 累积数据
        self._accumulated_data = {
            'topic': topic,
            'task_id': task_id,
        }

        total_skills = len(self.skills)
        yield PipelineEvent(
            event="start",
            metadata={
                "pipeline": self.name,
                "total_steps": total_skills,
                "run_id": self._context.run_id,
                "task_id": task_id
            }
        )

        try:
            # ===== Step 1: 大纲生成 =====
            outline_skill = self.get_skill('outline')
            if outline_skill and not self._should_skip_skill('outline'):
                yield PipelineEvent(
                    event="progress",
                    step=1,
                    skill="outline",
                    progress=0.1,
                    metadata={"status": "running", "message": "正在生成大纲..."}
                )

                outline_result = outline_skill.execute(
                    {'topic': topic, 'images': images},
                    {'pipeline': self.name, 'run_id': self._context.run_id}
                )
                self._context.results['outline'] = outline_result

                if not outline_result.success:
                    yield PipelineEvent(
                        event="error",
                        step=1,
                        skill="outline",
                        error=outline_result.error
                    )
                    self._status = PipelineStatus.FAILED
                    yield PipelineEvent(
                        event="finish",
                        result={"success": False, "error": outline_result.error}
                    )
                    return

                # 累积大纲数据
                outline_data = outline_result.data
                self._accumulated_data['outline'] = outline_data.get('outline', '')
                self._accumulated_data['pages'] = outline_data.get('pages', [])

                yield PipelineEvent(
                    event="step_complete",
                    step=1,
                    skill="outline",
                    result=outline_result.to_dict(),
                    progress=0.33,
                    metadata={"page_count": len(self._accumulated_data['pages'])}
                )

            # ===== Step 2: 内容生成 =====
            content_skill = self.get_skill('content')
            if content_skill and not self._should_skip_skill('content'):
                yield PipelineEvent(
                    event="progress",
                    step=2,
                    skill="content",
                    progress=0.4,
                    metadata={"status": "running", "message": "正在生成标题和文案..."}
                )

                content_result = content_skill.execute(
                    {
                        'topic': topic,
                        'outline': self._accumulated_data.get('outline', '')
                    },
                    {'pipeline': self.name, 'run_id': self._context.run_id}
                )
                self._context.results['content'] = content_result

                if not content_result.success:
                    yield PipelineEvent(
                        event="error",
                        step=2,
                        skill="content",
                        error=content_result.error
                    )
                    self._status = PipelineStatus.FAILED
                    yield PipelineEvent(
                        event="finish",
                        result={"success": False, "error": content_result.error}
                    )
                    return

                # 累积内容数据
                content_data = content_result.data
                self._accumulated_data['titles'] = content_data.get('titles', [])
                self._accumulated_data['copywriting'] = content_data.get('copywriting', '')
                self._accumulated_data['tags'] = content_data.get('tags', [])

                yield PipelineEvent(
                    event="step_complete",
                    step=2,
                    skill="content",
                    result=content_result.to_dict(),
                    progress=0.5,
                    metadata={
                        "title_count": len(self._accumulated_data['titles']),
                        "tag_count": len(self._accumulated_data['tags'])
                    }
                )

            # ===== Step 3: 图片生成 =====
            image_skill = self.get_skill('generate_image')
            if image_skill and not self._should_skip_skill('generate_image'):
                yield PipelineEvent(
                    event="progress",
                    step=3,
                    skill="generate_image",
                    progress=0.55,
                    metadata={"status": "running", "message": "正在生成图片..."}
                )

                # 图片生成使用 run_stream 以支持实时进度
                pages = self._accumulated_data.get('pages', [])
                image_input = {
                    'pages': pages,
                    'task_id': task_id,
                    'full_outline': self._accumulated_data.get('outline', ''),
                    'user_images': images,
                    'user_topic': topic
                }

                # 转发图片生成的流式事件
                for img_event in image_skill.run_stream(image_input):
                    event_type = img_event.get('event', '')

                    if event_type == 'progress':
                        yield PipelineEvent(
                            event="image_progress",
                            step=3,
                            skill="generate_image",
                            metadata=img_event.get('data', {})
                        )
                    elif event_type == 'complete':
                        yield PipelineEvent(
                            event="image_complete",
                            step=3,
                            skill="generate_image",
                            metadata=img_event.get('data', {})
                        )
                    elif event_type == 'error':
                        yield PipelineEvent(
                            event="image_error",
                            step=3,
                            skill="generate_image",
                            error=img_event.get('data', {}).get('message'),
                            metadata=img_event.get('data', {})
                        )
                    elif event_type == 'finish':
                        img_result = img_event.get('data', {})
                        self._accumulated_data['images'] = img_result.get('images', [])
                        self._accumulated_data['image_task_id'] = img_result.get('task_id')

                        # 创建 SkillResult 用于记录
                        self._context.results['generate_image'] = SkillResult(
                            success=img_result.get('success', False),
                            data=img_result
                        )

                        yield PipelineEvent(
                            event="step_complete",
                            step=3,
                            skill="generate_image",
                            result=img_result,
                            progress=1.0,
                            metadata={
                                "completed": img_result.get('completed', 0),
                                "failed": img_result.get('failed', 0)
                            }
                        )

            # ===== 完成 =====
            self._status = PipelineStatus.SUCCESS
            self._context.end_time = time.time()

            final_result = {
                "success": True,
                "data": self._accumulated_data,
                "task_id": task_id
            }

            yield PipelineEvent(
                event="finish",
                result=final_result,
                metadata={
                    "elapsed_time": self._context.elapsed_time,
                    "total_steps": total_skills
                }
            )

        except Exception as e:
            logger.exception(f"流水线执行异常: {e}")
            self._status = PipelineStatus.FAILED
            if self._context:
                self._context.end_time = time.time()

            yield PipelineEvent(
                event="error",
                error=str(e),
                metadata={"exception_type": type(e).__name__}
            )
            yield PipelineEvent(
                event="finish",
                result={"success": False, "error": str(e)}
            )

    def get_accumulated_data(self) -> Dict[str, Any]:
        """获取累积的数据"""
        return self._accumulated_data.copy()
