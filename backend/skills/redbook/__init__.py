"""
小红书图文生成专用技能

- OutlineSkill: 大纲生成技能
- ContentSkill: 内容生成技能（标题、文案、标签）
"""

from .outline import OutlineSkill
from .content import ContentSkill

__all__ = ['OutlineSkill', 'ContentSkill']
