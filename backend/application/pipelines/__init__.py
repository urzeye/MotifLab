"""
流水线层

流水线通过组合技能(Skills)实现复杂的端到端处理流程。
每个流水线专注于一个特定的应用场景。

可用流水线：
- RedBookPipeline: 小红书图文生成流水线
- ConceptPipeline: 概念图生成流水线
"""

from .redbook_pipeline import RedBookPipeline
from .concept_pipeline import ConceptPipeline

__all__ = ['RedBookPipeline', 'ConceptPipeline']
