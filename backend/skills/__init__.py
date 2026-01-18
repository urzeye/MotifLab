"""
Skills 技能层

技能是可复用的原子化处理单元，每个技能专注于一个特定任务。
技能可以被流水线组合使用，实现复杂的处理流程。

通用技能：
- AnalyzeSkill: 文本分析技能
- DesignSkill: 设计方案生成技能
- GenerateImageSkill: 图像生成技能

专用技能：
- redbook/: 小红书图文专用技能
- concept/: 概念图专用技能
"""

from backend.core.base_skill import BaseSkill, SkillResult, SkillStatus

# 通用技能
from .analyze import AnalyzeSkill
from .design import DesignSkill
from .generate import GenerateImageSkill

# 小红书专用技能
from .redbook import OutlineSkill, ContentSkill

# 概念图专用技能 (暂时为空，后续实现)
# from .concept import MapFrameworkSkill, DiscoverSkill

__all__ = [
    # 基类
    'BaseSkill',
    'SkillResult',
    'SkillStatus',
    # 通用技能
    'AnalyzeSkill',
    'DesignSkill',
    'GenerateImageSkill',
    # 小红书技能
    'OutlineSkill',
    'ContentSkill',
]
