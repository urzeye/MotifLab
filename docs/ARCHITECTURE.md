# RenderInk + Concept Visualizer 统一架构设计方案

> 本文档描述将 RenderInk（小红书图文生成器）与 Concept Visualizer Agent（科学概念图生成器）完全合并重构为统一平台的技术方案。

---

## 1. 项目背景

### 1.1 现有项目

| 项目 | 定位 | 技术栈 |
|------|------|--------|
| **RenderInk** | 小红书风格图文生成 | Flask + Vue 3 |
| **Concept Visualizer** | 科学概念图生成 | Python CLI Agent |

### 1.2 整合目标

- **统一架构**：不是简单嵌入，而是完全重构为统一的技术架构
- **多模式支持**：支持小红书图文、概念图、自定义等多种生成模式
- **知识库共享**：统一的理论框架、图表类型、视觉风格管理
- **配置统一**：复用现有的 API 配置和环境变量

---

## 2. 统一架构设计

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Vue 3)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  小红书   │  │  概念图   │  │ 知识库管理 │  │  历史记录  │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (Flask)                       │
│  /api/pipeline/*    /api/knowledge/*    /api/history/*      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Service Layer                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐│
│  │ PipelineService │  │ KnowledgeService│  │HistoryService││
│  └─────────────────┘  └─────────────────┘  └──────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Pipeline Layer                           │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐│
│  │RedBookPipeline │  │ConceptPipeline │  │ CustomPipeline ││
│  └────────────────┘  └────────────────┘  └────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Skill Layer                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Analyze  │  │  Design  │  │ Generate │  │  ...更多   │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│               Core Layer (Clients + Knowledge)               │
│  ┌─────────────────────┐      ┌─────────────────────┐      │
│  │   ClientFactory     │      │     Registry        │      │
│  │ (Text/Image APIs)   │      │ (Frameworks/Charts) │      │
│  └─────────────────────┘      └─────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 目录结构

```
backend/
├── app.py                      # Flask 应用入口
├── config/
│   ├── __init__.py
│   ├── settings.py             # 统一配置管理类
│   └── providers.yaml          # 服务商配置
│
├── core/                       # 核心抽象层
│   ├── __init__.py
│   ├── base_skill.py           # 技能抽象基类
│   ├── base_pipeline.py        # 流水线抽象基类
│   ├── base_client.py          # API 客户端抽象基类
│   └── events.py               # 事件/进度通知系统
│
├── clients/                    # 统一 API 客户端
│   ├── __init__.py
│   ├── factory.py              # 客户端工厂
│   ├── text/                   # 文本生成客户端
│   └── image/                  # 图像生成客户端
│
├── knowledge/                  # 知识库（来自 Concept Viz）
│   ├── __init__.py
│   ├── registry.py             # 注册中心（单例）
│   ├── frameworks/             # 理论框架库 YAML
│   ├── chart_types/            # 图表类型库 YAML
│   └── visual_styles/          # 视觉风格库 YAML
│
├── skills/                     # 技能层
│   ├── __init__.py
│   ├── analyze.py              # 分析技能（通用）
│   ├── design.py               # 设计技能（通用）
│   ├── generate.py             # 图像生成技能（通用）
│   ├── redbook/                # 小红书专用技能
│   │   ├── __init__.py
│   │   ├── outline.py          # 大纲生成
│   │   └── content.py          # 内容生成
│   └── concept/                # 概念图专用技能
│       ├── __init__.py
│       ├── map_framework.py    # 框架映射
│       └── discover.py         # 框架发现
│
├── pipelines/                  # 流水线层
│   ├── __init__.py
│   ├── redbook_pipeline.py     # 小红书图文流水线
│   ├── concept_pipeline.py     # 概念图流水线
│   └── custom_pipeline.py      # 自定义流水线
│
├── services/                   # 服务层
│   ├── __init__.py
│   ├── pipeline_service.py     # 流水线服务
│   ├── history_service.py      # 历史记录服务
│   └── knowledge_service.py    # 知识库管理服务
│
└── routes/                     # API 路由层
    ├── __init__.py
    ├── pipeline_routes.py
    ├── history_routes.py
    └── knowledge_routes.py
```

---

## 3. 核心设计模式

### 3.1 技能基类 (BaseSkill)

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseSkill(ABC):
    """技能抽象基类"""

    name: str = "base_skill"
    description: str = ""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    @abstractmethod
    def run(self, input_data: Any, context: Dict = None) -> Dict[str, Any]:
        """执行技能"""
        pass
```

### 3.2 流水线基类 (BasePipeline)

```python
from typing import Dict, Any, List, Generator

class BasePipeline(ABC):
    """流水线抽象基类"""

    name: str = "base_pipeline"
    skills: List[BaseSkill] = []

    def run_stream(self, input_data: Any) -> Generator[Dict, None, None]:
        """流式执行（支持 SSE）"""
        for i, skill in enumerate(self.skills):
            yield {"event": "progress", "step": i + 1, "skill": skill.name}
            result = skill.run(input_data)
            yield {"event": "complete", "step": i + 1, "result": result}
            input_data = result
        yield {"event": "finish", "success": True}
```

### 3.3 客户端工厂 (ClientFactory)

```python
class ClientFactory:
    """统一的客户端工厂"""

    _text_clients: Dict[str, type] = {}
    _image_clients: Dict[str, type] = {}

    @classmethod
    def get_text_client(cls, provider_config: Dict) -> BaseTextClient:
        """获取文本生成客户端"""
        pass

    @classmethod
    def get_image_client(cls, provider_config: Dict) -> BaseImageClient:
        """获取图像生成客户端"""
        pass
```

---

## 4. 流水线设计

### 4.1 小红书图文流水线

```
主题 → OutlineSkill → ContentSkill → GenerateImageSkill → 图文结果
         ↓                ↓                 ↓
       大纲结构      标题/文案/标签        封面+内容页
```

### 4.2 概念图流水线

```
文章 → AnalyzeSkill → MapFrameworkSkill → DesignSkill → GenerateImageSkill
          ↓                 ↓                 ↓                ↓
       概念提取          框架映射          设计方案          概念图
```

---

## 5. API 设计

### 5.1 流水线 API

```
POST /api/pipeline/run
{
  "pipeline": "redbook" | "concept",
  "input": { ... },
  "config": { "style": "blueprint" }
}

响应（SSE）：
event: progress → step_complete → finish
```

### 5.2 知识库 API

```
GET  /api/knowledge/frameworks
POST /api/knowledge/frameworks
GET  /api/knowledge/chart-types
GET  /api/knowledge/visual-styles
```

---

## 6. 前端页面结构

```
/                   → 首页（模式选择）
/redbook/*          → 小红书模式
/concept/*          → 概念图模式
/history            → 历史记录
/knowledge          → 知识库管理
/settings           → 系统设置
```

---

## 7. 实现步骤

### Phase 1: 基础架构
1. 创建 `core/` 核心抽象层
2. 创建 `clients/` 统一客户端
3. 创建 `config/` 统一配置

### Phase 2: 技能迁移
1. RenderInk 服务 → `skills/redbook/`
2. Concept Viz 技能 → `skills/concept/`
3. 知识库 → `knowledge/`

### Phase 3: 流水线实现
1. RedBookPipeline
2. ConceptPipeline

### Phase 4: API 层
1. `/api/pipeline/*` 路由
2. `/api/knowledge/*` 路由

### Phase 5: 前端重构
1. 首页模式选择
2. 概念图 UI
3. 知识库管理

---

## 8. 文件迁移映射

| 源文件 | 目标位置 |
|--------|----------|
| `services/outline.py` | `skills/redbook/outline.py` |
| `services/content.py` | `skills/redbook/content.py` |
| `services/image.py` | `skills/generate.py` |
| concept-viz `analyze.py` | `skills/analyze.py` |
| concept-viz `map_framework.py` | `skills/concept/map_framework.py` |
| concept-viz `registry.py` | `knowledge/registry.py` |
| concept-viz `frameworks/*.yaml` | `knowledge/frameworks/` |

---

*文档版本: v1.0*
*创建日期: 2026-01-18*
