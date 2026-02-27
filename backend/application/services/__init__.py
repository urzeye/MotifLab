"""应用层服务导出（延迟加载）。"""

from __future__ import annotations

from importlib import import_module

_SYMBOL_TO_MODULE = {
    "ProviderConfigService": "provider_config_service",
    "get_provider_config_service": "provider_config_service",
    "ConceptHistoryApplicationService": "concept_history_service",
    "get_concept_history_application_service": "concept_history_service",
    "ContentApplicationService": "content_application_service",
    "get_content_application_service": "content_application_service",
    "HistoryApplicationService": "history_application_service",
    "get_history_application_service": "history_application_service",
    "ImageGenerationApplicationService": "image_generation_application_service",
    "get_image_generation_application_service": "image_generation_application_service",
    "ImageJobApplicationService": "image_job_application_service",
    "get_image_job_application_service": "image_job_application_service",
    "KnowledgeApplicationService": "knowledge_application_service",
    "get_knowledge_application_service": "knowledge_application_service",
    "OutlineApplicationService": "outline_application_service",
    "get_outline_application_service": "outline_application_service",
    "PipelineApplicationService": "pipeline_application_service",
    "get_pipeline_application_service": "pipeline_application_service",
    "PublishApplicationService": "publish_application_service",
    "get_publish_application_service": "publish_application_service",
    "SearchApplicationService": "search_application_service",
    "get_search_application_service": "search_application_service",
    "TemplateApplicationService": "template_application_service",
    "get_template_application_service": "template_application_service",
}

__all__ = list(_SYMBOL_TO_MODULE.keys())


def __getattr__(name: str):
    """按需加载应用层符号，避免模块导入环。"""
    module_name = _SYMBOL_TO_MODULE.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(f"{__name__}.{module_name}")
    value = getattr(module, name)
    globals()[name] = value
    return value
