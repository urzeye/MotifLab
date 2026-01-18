"""
知识库管理模块
管理理论框架、图表类型和视觉风格
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List


class KnowledgeRegistry:
    """统一的知识库注册管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.frameworks: Dict[str, Any] = {}
        self.chart_types: Dict[str, Any] = {}
        self.visual_styles: Dict[str, Any] = {}

        # 知识库目录
        self.base_dir = Path(__file__).parent
        self.frameworks_dir = self.base_dir / "frameworks"
        self.chart_types_dir = self.base_dir / "chart_types"
        self.visual_styles_dir = self.base_dir / "visual_styles"

        self._load_all()
        self._initialized = True

    def _load_yaml_files(self, directory: Path) -> Dict[str, Any]:
        """从目录加载所有YAML文件"""
        items = {}
        if not directory.exists():
            return items

        for ext in ["*.yaml", "*.yml"]:
            for file in directory.glob(ext):
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        if data:
                            item_id = data.get("id", file.stem)
                            items[item_id] = data
                except Exception as e:
                    print(f"Warning: Failed to load {file}: {e}")

        return items

    def _load_all(self):
        """加载所有配置"""
        # 加载默认配置
        self.frameworks = DEFAULT_FRAMEWORKS.copy()
        self.chart_types = DEFAULT_CHART_TYPES.copy()
        self.visual_styles = DEFAULT_VISUAL_STYLES.copy()

        # 加载自定义YAML文件（会覆盖默认）
        custom_frameworks = self._load_yaml_files(self.frameworks_dir)
        self.frameworks.update(custom_frameworks)

        custom_charts = self._load_yaml_files(self.chart_types_dir)
        self.chart_types.update(custom_charts)

        custom_styles = self._load_yaml_files(self.visual_styles_dir)
        self.visual_styles.update(custom_styles)

    def reload(self):
        """重新加载所有配置"""
        self._load_all()

    # =========================================================================
    # 框架相关方法
    # =========================================================================

    def get_framework(self, framework_id: str) -> Optional[Dict]:
        """获取单个框架"""
        return self.frameworks.get(framework_id)

    def list_frameworks(self) -> List[Dict]:
        """列出所有框架（返回列表格式）"""
        return [
            {"id": k, **v}
            for k, v in self.frameworks.items()
        ]

    def add_framework(self, framework_id: str, framework_data: Dict, persist: bool = False):
        """添加新框架"""
        self.frameworks[framework_id] = framework_data

        if persist:
            self.frameworks_dir.mkdir(parents=True, exist_ok=True)
            file_path = self.frameworks_dir / f"{framework_id}.yaml"
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(framework_data, f, allow_unicode=True, default_flow_style=False)

    def get_frameworks_for_prompt(self) -> str:
        """生成供LLM使用的框架描述"""
        lines = []
        for fid, f in self.frameworks.items():
            lines.append(f"### {f.get('name', fid)} (ID: {fid})")
            lines.append(f"- 描述: {f.get('description', 'N/A')}")
            lines.append(f"- 关键词: {', '.join(f.get('keywords', []))}")
            lines.append(f"- 视觉元素: {', '.join(f.get('visual_elements', []))}")
            lines.append(f"- 适用场景: {f.get('use_when', 'N/A')}")
            if f.get('canonical_chart'):
                suggested = f.get('suggested_charts', [])
                suggested_str = f", 备选: {', '.join(suggested)}" if suggested else ""
                lines.append(f"- 推荐图表: {f.get('canonical_chart')}{suggested_str}")
            lines.append("")
        return "\n".join(lines)

    # =========================================================================
    # 图表类型相关方法
    # =========================================================================

    def get_chart_type(self, chart_id: str) -> Optional[Dict]:
        """获取单个图表类型"""
        return self.chart_types.get(chart_id)

    def list_chart_types(self) -> List[Dict]:
        """列出所有图表类型（返回列表格式）"""
        return [
            {"id": k, **v}
            for k, v in self.chart_types.items()
        ]

    def get_chart_types_for_prompt(self) -> str:
        """生成供LLM使用的图表类型描述"""
        lines = []
        for cid, c in self.chart_types.items():
            lines.append(f"- **{cid}** ({c.get('name', cid)}): {c.get('description', 'N/A')}")
            lines.append(f"  适用于: {', '.join(c.get('best_for', []))}")
        return "\n".join(lines)

    # =========================================================================
    # 视觉风格相关方法
    # =========================================================================

    def get_visual_style(self, style_id: str = None) -> Dict:
        """获取视觉风格"""
        style_id = style_id or "blueprint"
        return self.visual_styles.get(style_id, self.visual_styles.get("blueprint", {}))

    def list_visual_styles(self) -> List[Dict]:
        """列出所有视觉风格（返回列表格式）"""
        return [
            {"id": k, **v}
            for k, v in self.visual_styles.items()
        ]


# =============================================================================
# 默认内置框架
# =============================================================================

DEFAULT_FRAMEWORKS = {
    "agapism": {
        "name": "Agapism (爱智论)",
        "name_en": "Agapism",
        "origin": "Charles Sanders Peirce",
        "description": "通过吸引/爱/内在驱动实现发展，而非外部强制",
        "keywords": ["attraction", "love", "internal motivation", "identity", "desire"],
        "visual_elements": ["magnetic field lines", "attractor basin", "flowing curves"],
        "use_when": "概念涉及内在动机、价值认同、自发趋向",
        "canonical_chart": "attractor",
        "suggested_charts": ["network", "terrain"]
    },
    "anancism": {
        "name": "Anancism (必然论)",
        "name_en": "Anancism",
        "origin": "Charles Sanders Peirce",
        "description": "通过规则、约束、机械因果实现控制",
        "keywords": ["rules", "constraints", "mechanical", "rigid", "necessity"],
        "visual_elements": ["geometric lattice", "rigid structures", "interlocking beams"],
        "use_when": "概念涉及硬性规则、机械约束、强制执行",
        "canonical_chart": "matrix",
        "suggested_charts": ["flowchart", "network"]
    },
    "goodhart": {
        "name": "Goodhart's Law (古德哈特定律)",
        "name_en": "Goodhart's Law",
        "origin": "Charles Goodhart",
        "description": "当度量成为目标时，它就不再是好的度量",
        "keywords": ["metric", "optimization", "gaming", "proxy", "target"],
        "visual_elements": ["diverging lines", "gap visualization", "optimization curves"],
        "use_when": "概念涉及优化陷阱、指标失效、目标与度量的偏离",
        "canonical_chart": "comparison",
        "suggested_charts": ["terrain", "timeline"]
    },
    "moloch": {
        "name": "Moloch Trap (莫洛克陷阱)",
        "name_en": "Moloch Trap",
        "origin": "Scott Alexander / Coordination Theory",
        "description": "个体理性导致集体非理性的协调失败",
        "keywords": ["coordination", "collective", "trap", "race", "competition"],
        "visual_elements": ["converging arrows", "trap structure", "race to bottom"],
        "use_when": "概念涉及协调失败、竞争困境、集体行动问题",
        "canonical_chart": "terrain",
        "suggested_charts": ["network", "cycle"]
    },
    "multi_scale": {
        "name": "Multi-Scale Alignment (多尺度对齐)",
        "name_en": "Multi-Scale Alignment",
        "origin": "Systems Theory / AI Alignment",
        "description": "不同层级目标之间的协调与约束传递",
        "keywords": ["hierarchy", "levels", "priority", "constraint", "scale"],
        "visual_elements": ["pyramid", "layered structure", "bidirectional arrows"],
        "use_when": "概念涉及层级结构、优先级排序、跨层级协调",
        "canonical_chart": "pyramid",
        "suggested_charts": ["flowchart", "network"]
    },
    "circuit_breaker": {
        "name": "Circuit Breaker (断路器模式)",
        "name_en": "Circuit Breaker Pattern",
        "origin": "Software Engineering / Resilience Patterns",
        "description": "检测异常并自动中断以防止级联失败",
        "keywords": ["detect", "stop", "reset", "monitor", "safeguard"],
        "visual_elements": ["flowchart with decision", "stop sign", "feedback loop"],
        "use_when": "概念涉及安全机制、自检系统、异常处理",
        "canonical_chart": "flowchart",
        "suggested_charts": ["cycle", "comparison"]
    },
    "attractor": {
        "name": "Attractor Dynamics (吸引子动力学)",
        "name_en": "Attractor Dynamics",
        "origin": "Dynamical Systems Theory",
        "description": "系统自然趋向某些稳定状态的倾向",
        "keywords": ["basin", "valley", "landscape", "convergence", "stability"],
        "visual_elements": ["3D terrain", "valleys and peaks", "basin of attraction"],
        "use_when": "概念涉及稳定状态、自然趋向、能量最小化",
        "canonical_chart": "terrain",
        "suggested_charts": ["attractor", "network"]
    }
}

# =============================================================================
# 默认图表类型
# =============================================================================

DEFAULT_CHART_TYPES = {
    "pyramid": {
        "name": "金字塔图",
        "name_en": "Pyramid Chart",
        "description": "展示层级关系或优先级排序",
        "best_for": ["hierarchy", "priority", "levels", "importance ranking"]
    },
    "comparison": {
        "name": "对比图",
        "name_en": "Comparison Chart",
        "description": "展示二元对比或对立概念",
        "best_for": ["contrast", "versus", "binary", "trade-off"]
    },
    "network": {
        "name": "网络图",
        "name_en": "Network Diagram",
        "description": "展示系统关系或多元连接",
        "best_for": ["relationships", "system", "connections", "dependencies"]
    },
    "flowchart": {
        "name": "流程图",
        "name_en": "Flowchart",
        "description": "展示过程、决策或状态转换",
        "best_for": ["process", "decision", "workflow", "state machine"]
    },
    "terrain": {
        "name": "地形图/热力图",
        "name_en": "Terrain/Heatmap",
        "description": "展示优化空间或权衡关系",
        "best_for": ["optimization", "trade-off", "landscape", "gradient"]
    },
    "attractor": {
        "name": "吸引子图",
        "name_en": "Attractor Diagram",
        "description": "展示吸引/收敛/磁场效应",
        "best_for": ["attraction", "convergence", "magnetic", "gravity"]
    },
    "timeline": {
        "name": "时间线",
        "name_en": "Timeline",
        "description": "展示时序发展或阶段演进",
        "best_for": ["temporal", "evolution", "phases", "milestones"]
    },
    "venn": {
        "name": "韦恩图",
        "name_en": "Venn Diagram",
        "description": "展示集合关系或概念重叠",
        "best_for": ["overlap", "intersection", "sets", "shared properties"]
    },
    "matrix": {
        "name": "矩阵图",
        "name_en": "Matrix Chart",
        "description": "展示二维分类或象限分析",
        "best_for": ["2x2 analysis", "classification", "quadrants", "positioning"]
    },
    "cycle": {
        "name": "循环图",
        "name_en": "Cycle Diagram",
        "description": "展示循环过程或反馈回路",
        "best_for": ["cycle", "feedback", "loop", "recurring process"]
    }
}

# =============================================================================
# 默认视觉风格
# =============================================================================

DEFAULT_VISUAL_STYLES = {
    "blueprint": {
        "name": "技术蓝图风格",
        "description": "工程图纸风格，适合技术/学术内容",
        "colors": {
            "primary": "#2F337",
            "secondary": "#8B7355",
            "background": "#F5F0E1"
        },
        "style_prefix": """Technical blueprint-style infographic on aged cream paper.
Title in dark maroon ALL CAPS. Teal and brown color scheme.
Clean technical illustration with bilingual labels."""
    },
    "modern": {
        "name": "现代简约风格",
        "description": "简洁现代，适合商业演示",
        "colors": {
            "primary": "#1A365D",
            "secondary": "#38B2AC",
            "background": "#F8F9FA"
        },
        "style_prefix": """Modern minimalist infographic with clean white background.
Bold sans-serif typography. Flat design with sharp edges."""
    },
    "academic": {
        "name": "学术论文风格",
        "description": "严谨学术，适合研究内容",
        "colors": {
            "primary": "#000000",
            "secondary": "#1A365D",
            "background": "#FFFFFF"
        },
        "style_prefix": """Academic paper figure style with minimal decoration.
High contrast, clear labels, suitable for publication."""
    },
    "creative": {
        "name": "创意艺术风格",
        "description": "艺术感强，适合创意内容",
        "colors": {
            "primary": "#805AD5",
            "secondary": "#ED64A6",
            "background": "#1A202C"
        },
        "style_prefix": """Creative artistic infographic with gradient backgrounds.
Modern artistic style with subtle 3D effects and glows."""
    }
}


# 单例实例
registry = KnowledgeRegistry()

# 导出
__all__ = ["KnowledgeRegistry", "registry"]
