"""
概念可视化技能模块

将文章转化为概念图的完整技能集：
- ConceptAnalyzeSkill: 分析文章提取核心概念
- ConceptMapSkill: 将概念映射到理论框架
- ConceptDesignSkill: 设计可视化方案和生成提示词
- ConceptGenerateSkill: 生成概念图图像
"""

from .analyze import ConceptAnalyzeSkill
from .map_framework import ConceptMapSkill
from .design import ConceptDesignSkill
from .generate import ConceptGenerateSkill

__all__ = [
    "ConceptAnalyzeSkill",
    "ConceptMapSkill",
    "ConceptDesignSkill",
    "ConceptGenerateSkill"
]
