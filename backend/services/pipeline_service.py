"""
流水线服务

提供流水线的创建、执行和管理功能。
"""

import logging
from typing import Any, Dict, Generator, Optional

from backend.pipelines import RedBookPipeline, ConceptPipeline
from backend.core.base_pipeline import BasePipeline, PipelineEvent
from backend.config import Config

logger = logging.getLogger(__name__)


class PipelineService:
    """流水线服务类"""

    # 可用的流水线类型
    PIPELINE_TYPES = {
        'redbook': RedBookPipeline,
        'concept': ConceptPipeline,
    }

    def __init__(self):
        self._active_pipelines: Dict[str, BasePipeline] = {}

    def _get_provider_configs(self) -> Dict[str, Any]:
        """获取服务商配置"""
        config = {}

        # 获取文本服务商配置
        try:
            text_provider = Config.get_active_text_provider()
            config['text_provider'] = Config.get_text_provider_config(text_provider)
        except Exception as e:
            logger.warning(f"获取文本服务商配置失败: {e}")
            config['text_provider'] = {}

        # 获取图片服务商配置
        try:
            image_provider = Config.get_active_image_provider()
            config['image_provider'] = Config.get_image_provider_config(image_provider)
        except Exception as e:
            logger.warning(f"获取图片服务商配置失败: {e}")
            config['image_provider'] = {}

        return config

    def create_pipeline(
        self,
        pipeline_type: str,
        config: Optional[Dict[str, Any]] = None
    ) -> BasePipeline:
        """
        创建流水线实例

        Args:
            pipeline_type: 流水线类型 ('redbook', 'concept')
            config: 额外配置

        Returns:
            流水线实例
        """
        if pipeline_type not in self.PIPELINE_TYPES:
            available = ', '.join(self.PIPELINE_TYPES.keys())
            raise ValueError(f"未知的流水线类型: {pipeline_type}，可用类型: {available}")

        pipeline_class = self.PIPELINE_TYPES[pipeline_type]

        # 合并配置
        full_config = self._get_provider_configs()
        if config:
            full_config.update(config)

        return pipeline_class(config=full_config)

    def run_pipeline(
        self,
        pipeline_type: str,
        input_data: Any,
        config: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        同步执行流水线

        Args:
            pipeline_type: 流水线类型
            input_data: 输入数据
            config: 额外配置
            context: 执行上下文

        Returns:
            执行结果
        """
        pipeline = self.create_pipeline(pipeline_type, config)
        return pipeline.run(input_data, context)

    def run_pipeline_stream(
        self,
        pipeline_type: str,
        input_data: Any,
        config: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Generator[PipelineEvent, None, None]:
        """
        流式执行流水线（支持 SSE）

        Args:
            pipeline_type: 流水线类型
            input_data: 输入数据
            config: 额外配置
            context: 执行上下文

        Yields:
            PipelineEvent 事件
        """
        pipeline = self.create_pipeline(pipeline_type, config)
        run_id = None

        for event in pipeline.run_stream(input_data, context):
            # 记录活跃的流水线
            if event.event == "start" and event.metadata:
                run_id = event.metadata.get('run_id')
                if run_id:
                    self._active_pipelines[run_id] = pipeline

            yield event

            # 清理已完成的流水线
            if event.event == "finish" and run_id:
                self._active_pipelines.pop(run_id, None)

    def get_active_pipeline(self, run_id: str) -> Optional[BasePipeline]:
        """获取活跃的流水线实例"""
        return self._active_pipelines.get(run_id)

    def cancel_pipeline(self, run_id: str) -> bool:
        """取消正在执行的流水线"""
        pipeline = self._active_pipelines.get(run_id)
        if pipeline:
            return pipeline.cancel()
        return False

    @classmethod
    def get_available_pipelines(cls) -> Dict[str, str]:
        """获取可用的流水线列表"""
        return {
            name: cls.PIPELINE_TYPES[name].description
            for name in cls.PIPELINE_TYPES
        }


# 全局服务实例
_service_instance: Optional[PipelineService] = None


def get_pipeline_service() -> PipelineService:
    """获取全局流水线服务实例"""
    global _service_instance
    if _service_instance is None:
        _service_instance = PipelineService()
    return _service_instance
