"""
概念图生成流水线

流程：文章 → ConceptAnalyzeSkill → ConceptMapSkill → ConceptDesignSkill → ConceptGenerateSkill → 完整概念图集
"""

import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from backend.core.base_pipeline import BasePipeline, PipelineEvent, PipelineContext, PipelineStatus
from backend.core.base_skill import BaseSkill, SkillResult
from backend.skills.concept import (
    ConceptAnalyzeSkill,
    ConceptMapSkill,
    ConceptDesignSkill,
    ConceptGenerateSkill
)
from backend.skills.concept.analyze import AnalyzeInput
from backend.skills.concept.map_framework import MapInput
from backend.skills.concept.design import DesignInput
from backend.skills.concept.generate import GenerateInput

logger = logging.getLogger(__name__)


class ConceptPipeline(BasePipeline):
    """
    概念图生成流水线

    输入：
    {
        "article": "文章内容或文件路径",
        "style": "blueprint",  # 可选：视觉风格
        "config": {            # 可选配置
            "skip_generate": bool,  # 跳过图像生成
            "max_concepts": int,    # 最大概念数
        }
    }

    输出：
    {
        "main_theme": "主题",
        "concepts": [...],
        "mappings": [...],
        "designs": [...],
        "images": [...],
        "task_id": "..."
    }
    """

    name = "concept"
    description = "概念图生成流水线"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._accumulated_data: Dict[str, Any] = {}

    def build_skills(self) -> List[BaseSkill]:
        """构建技能列表"""
        text_config = self.config.get('text_provider', {})
        image_config = self.config.get('image_provider', {})
        style = self.config.get('style', 'blueprint')

        return [
            ConceptAnalyzeSkill(config={'text_provider': text_config}),
            ConceptMapSkill(config={'text_provider': text_config}),
            ConceptDesignSkill(config={'text_provider': text_config}, style=style),
            ConceptGenerateSkill(config={'image_provider': image_config}, style=style),
        ]

    def _should_skip_skill(self, skill_name: str) -> bool:
        """检查是否应跳过某个技能"""
        pipeline_config = self.config.get('pipeline', {})
        if skill_name == 'concept_generate' and pipeline_config.get('skip_generate'):
            return True
        return False

    def run_stream(
        self,
        input_data: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> Generator[PipelineEvent, None, None]:
        """
        流式执行概念图生成流水线

        特殊处理：
        1. 在技能之间传递和累积数据
        2. 图像生成技能使用其特有的 run_stream 方法
        """
        # 初始化上下文
        self._context = PipelineContext()
        if context:
            self._context.variables.update(context)
        self._context.start_time = time.time()
        self._status = PipelineStatus.RUNNING

        # 解析输入
        if isinstance(input_data, dict):
            article = input_data.get('article', '')
            style = input_data.get('style', 'blueprint')
            task_id = input_data.get('task_id', f"concept_{uuid.uuid4().hex[:8]}")
            max_concepts = input_data.get('config', {}).get('max_concepts', 8)
        else:
            article = str(input_data)
            style = 'blueprint'
            task_id = f"concept_{uuid.uuid4().hex[:8]}"
            max_concepts = 8

        # 更新技能配置中的 style
        self.config['style'] = style
        # 重建技能列表以应用新配置
        self.skills = self.build_skills()

        # 累积数据
        self._accumulated_data = {
            'article': article,
            'style': style,
            'task_id': task_id,
        }

        total_skills = len(self.skills)
        yield PipelineEvent(
            event="start",
            metadata={
                "pipeline": self.name,
                "total_steps": total_skills,
                "run_id": self._context.run_id,
                "task_id": task_id,
                "style": style
            }
        )

        current_data = article
        step_names = ["analyze", "map", "design", "generate"]

        for step_index, skill in enumerate(self.skills):
            step_name = step_names[step_index] if step_index < len(step_names) else skill.name

            # 检查是否跳过
            if self._should_skip_skill(skill.name):
                yield PipelineEvent(
                    event="skip",
                    step=step_index + 1,
                    skill=skill.name,
                    metadata={"reason": "配置跳过"}
                )
                continue

            yield PipelineEvent(
                event="step_start",
                step=step_index + 1,
                skill=skill.name,
                progress=(step_index / total_skills),
                metadata={"step_name": step_name}
            )

            try:
                # 根据技能类型准备输入
                skill_input = self._prepare_skill_input(skill.name, current_data, max_concepts)

                # 图像生成使用流式
                if isinstance(skill, ConceptGenerateSkill):
                    for gen_event in skill.run_stream(skill_input):
                        # 转换为 PipelineEvent
                        yield PipelineEvent(
                            event=f"generate_{gen_event.get('type', 'progress')}",
                            step=step_index + 1,
                            skill=skill.name,
                            result=gen_event,
                            progress=(step_index + gen_event.get('index', 0) / max(gen_event.get('total', 1), 1)) / total_skills
                        )

                    # 获取最终结果
                    result = SkillResult(
                        success=True,
                        data=self._accumulated_data.get('generate_results', {}),
                        message="图像生成完成"
                    )
                else:
                    # 普通技能执行
                    result = skill.run(skill_input)

                if not result.success:
                    yield PipelineEvent(
                        event="step_error",
                        step=step_index + 1,
                        skill=skill.name,
                        error=result.error or "技能执行失败"
                    )
                    self._status = PipelineStatus.FAILED
                    yield PipelineEvent(
                        event="error",
                        error=f"{skill.name} 执行失败: {result.error}"
                    )
                    return

                # 累积结果
                self._accumulated_data[step_name] = result.data
                current_data = result.data

                yield PipelineEvent(
                    event="step_complete",
                    step=step_index + 1,
                    skill=skill.name,
                    result=self._summarize_result(skill.name, result),
                    progress=((step_index + 1) / total_skills)
                )

            except Exception as e:
                logger.exception(f"技能 {skill.name} 执行异常")
                yield PipelineEvent(
                    event="step_error",
                    step=step_index + 1,
                    skill=skill.name,
                    error=str(e)
                )
                self._status = PipelineStatus.FAILED
                yield PipelineEvent(
                    event="error",
                    error=f"{skill.name} 执行异常: {str(e)}"
                )
                return

        # 完成
        self._context.end_time = time.time()
        self._status = PipelineStatus.SUCCESS

        # 构建最终输出
        final_output = self._build_final_output()

        yield PipelineEvent(
            event="complete",
            result=final_output,
            progress=1.0,
            metadata={
                "elapsed_time": self._context.elapsed_time,
                "task_id": task_id
            }
        )

    def _prepare_skill_input(self, skill_name: str, current_data: Any, max_concepts: int):
        """为每个技能准备输入"""
        if skill_name == "concept_analyze":
            return AnalyzeInput(
                article=current_data,
                max_concepts=max_concepts
            )
        elif skill_name == "concept_map":
            return MapInput(concepts=current_data)
        elif skill_name == "concept_design":
            return DesignInput(
                mappings=current_data,
                style=self._accumulated_data.get('style', 'blueprint')
            )
        elif skill_name == "concept_generate":
            return GenerateInput(
                designs=current_data,
                style=self._accumulated_data.get('style', 'blueprint'),
                output_dir=f"output/concepts/{self._accumulated_data.get('task_id', 'default')}"
            )
        return current_data

    def _summarize_result(self, skill_name: str, result: SkillResult) -> Dict[str, Any]:
        """生成简洁的结果摘要用于事件"""
        data = result.data or {}

        if skill_name == "concept_analyze":
            return {
                "main_theme": data.get("main_theme"),
                "concept_count": len(data.get("key_concepts", []))
            }
        elif skill_name == "concept_map":
            return {
                "mapping_count": len(data.get("mappings", []))
            }
        elif skill_name == "concept_design":
            return {
                "design_count": len(data.get("designs", []))
            }
        elif skill_name == "concept_generate":
            return {
                "total": data.get("total", 0),
                "success_count": data.get("success_count", 0)
            }

        return {"message": result.message}

    def _build_final_output(self) -> Dict[str, Any]:
        """构建最终输出"""
        analyze_data = self._accumulated_data.get('analyze', {})
        map_data = self._accumulated_data.get('map', {})
        design_data = self._accumulated_data.get('design', {})
        generate_data = self._accumulated_data.get('generate', {})

        return {
            "task_id": self._accumulated_data.get('task_id'),
            "style": self._accumulated_data.get('style'),
            "main_theme": analyze_data.get('main_theme'),
            "concepts": analyze_data.get('key_concepts', []),
            "relationships": analyze_data.get('relationships', []),
            "mappings": map_data.get('mappings', []),
            "designs": design_data.get('designs', []),
            "images": generate_data.get('results', []) if generate_data else []
        }

    def run(
        self,
        input_data: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> SkillResult:
        """
        同步执行流水线（收集所有事件后返回）
        """
        final_result = None

        for event in self.run_stream(input_data, context):
            if event.event == "complete":
                final_result = event.result
            elif event.event == "error":
                return SkillResult(
                    success=False,
                    error=event.error
                )

        if final_result:
            return SkillResult(
                success=True,
                data=final_result,
                message="概念图生成完成"
            )

        return SkillResult(
            success=False,
            error="流水线执行异常"
        )
