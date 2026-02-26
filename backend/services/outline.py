import logging
import os
import re
import json
from typing import Dict, List, Any, Optional
from backend.config import Config
from backend.utils.text_client import get_text_chat_client

logger = logging.getLogger(__name__)


class OutlineService:
    def __init__(self):
        logger.debug("初始化 OutlineService...")
        # 加载完整文本配置（保留多服务商信息，便于按能力回退）
        self.text_config = Config.load_text_providers_config()
        # 启动时校验至少有一个可用服务商
        self._get_client()
        self.prompt_template = self._load_prompt_template()
        logger.info(f"OutlineService 初始化完成，使用服务商: {self.text_config.get('active_provider')}")

    def _is_provider_usable(self, provider_config: Dict[str, Any]) -> bool:
        """检查服务商配置是否可用（主要是 API Key）"""
        api_key = provider_config.get('api_key')
        if not api_key:
            return False
        if isinstance(api_key, str) and '${' in api_key and '}' in api_key:
            return False
        return True

    def _get_client(self, needs_image_support: bool = False):
        """根据配置获取客户端，必要时优先选择支持图片输入的服务商"""
        active_provider = self.text_config.get('active_provider', 'google_gemini')
        providers = self.text_config.get('providers', {})

        if not providers:
            logger.error("未找到任何文本生成服务商配置")
            raise ValueError(
                "未找到任何文本生成服务商配置。\n"
                "解决方案：\n"
                "1. 在系统设置页面添加文本生成服务商\n"
                "2. 或手动编辑 text_providers.yaml 文件"
            )

        ordered_provider_names = []
        if active_provider in providers:
            ordered_provider_names.append(active_provider)
        for name in providers.keys():
            if name != active_provider:
                ordered_provider_names.append(name)

        candidates = []
        for name in ordered_provider_names:
            provider_config = providers.get(name, {})
            if not self._is_provider_usable(provider_config):
                continue
            if needs_image_support and not provider_config.get('supports_images', True):
                continue
            candidates.append((name, provider_config))

        # 若无“支持图片”的候选，则降级到任意可用服务商（并提示）
        if needs_image_support and not candidates:
            logger.warning("未找到 supports_images=true 的可用文本服务商，降级使用默认可用服务商")
            for name in ordered_provider_names:
                provider_config = providers.get(name, {})
                if self._is_provider_usable(provider_config):
                    candidates.append((name, provider_config))

        if not candidates:
            available = ', '.join(providers.keys()) if providers else '无'
            raise ValueError(
                f"未找到可用的文本生成服务商配置。\n"
                f"可用的服务商: {available}\n"
                "解决方案：在系统设置中检查并填写有效 API Key"
            )

        provider_name, provider_config = candidates[0]
        logger.info(
            f"使用文本服务商: {provider_name} "
            f"(type={provider_config.get('type')}, supports_images={provider_config.get('supports_images', True)})"
        )
        return get_text_chat_client(provider_config), provider_name, provider_config

    def _load_prompt_template(self) -> str:
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "prompts",
            "outline_prompt.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _parse_outline(self, outline_text: str) -> List[Dict[str, Any]]:
        # 按 <page> 分割页面（兼容旧的 --- 分隔符）
        if '<page>' in outline_text:
            pages_raw = re.split(r'<page>', outline_text, flags=re.IGNORECASE)
        else:
            # 向后兼容：如果没有 <page> 则使用 ---
            pages_raw = outline_text.split("---")

        pages = []

        for index, page_text in enumerate(pages_raw):
            page_text = page_text.strip()
            if not page_text:
                continue

            page_type = "content"
            type_match = re.match(r"\[(\S+)\]", page_text)
            if type_match:
                type_cn = type_match.group(1)
                type_mapping = {
                    "封面": "cover",
                    "内容": "content",
                    "总结": "summary",
                }
                page_type = type_mapping.get(type_cn, "content")

            clean_content, embedded_suggestion = self._extract_embedded_image_suggestion(page_text)
            pages.append({
                "index": index,
                "type": page_type,
                "content": clean_content or page_text,
                "image_suggestion": embedded_suggestion or None
            })

        return pages

    def _extract_embedded_image_suggestion(self, content: str) -> tuple[str, Optional[str]]:
        """
        从页面文案中提取“配图建议”段落，避免与独立展示区域重复。

        规则：
        - 识别常见标题：配图建议 / 图片建议 / 画面建议 / 视觉建议
        - 命中后将该标题行及其后内容视为建议区（通常位于页尾）
        """
        text = str(content or "").replace("\r\n", "\n").strip()
        if not text:
            return "", None

        marker = re.search(
            r'(?im)^\s*(?:[-*+]\s*)?(?:【\s*)?(?:配图建议|图片建议|画面建议|视觉建议)(?:\s*】)?\s*(?:[:：]\s*)?(.*)$',
            text
        )
        if not marker:
            return text, None

        suggestion_inline = (marker.group(1) or "").strip()
        trailing = text[marker.end():].strip()

        parts = []
        if suggestion_inline:
            parts.append(suggestion_inline)
        if trailing:
            parts.append(trailing)
        suggestion = "\n".join(parts).strip()

        clean_content = text[:marker.start()].rstrip()
        clean_content = re.sub(r'\n{3,}', '\n\n', clean_content).strip()
        return clean_content, (suggestion or None)

    def _score_suggestion_text(self, text: str) -> int:
        """对建议文本做一个简易质量评分，用于冲突时择优。"""
        value = (text or "").strip()
        if not value:
            return 0

        detail_keywords = ["主体", "场景", "构图", "镜头", "光线", "色调", "风格", "氛围", "材质", "景别"]
        score = len(value)
        score += value.count("\n") * 8
        score += sum(20 for kw in detail_keywords if kw in value)
        return score

    def _merge_suggestion(self, primary: Optional[str], secondary: Optional[str]) -> Optional[str]:
        """
        合并两路建议文本（primary 优先），在不丢信息的前提下避免重复。
        """
        a = (primary or "").strip()
        b = (secondary or "").strip()

        if not a and not b:
            return None
        if not a:
            return b
        if not b:
            return a

        norm_a = re.sub(r'\s+', '', a)
        norm_b = re.sub(r'\s+', '', b)
        if norm_a == norm_b:
            return a if len(a) >= len(b) else b

        if norm_b in norm_a:
            return a
        if norm_a in norm_b:
            return b

        # 两者差异明显时择优保留信息更丰富的版本
        return a if self._score_suggestion_text(a) >= self._score_suggestion_text(b) else b

    def _build_source_reference(self, source_content: Optional[str]) -> str:
        """构造网页参考素材片段，避免超长输入导致模型失败。"""
        if not source_content:
            return ""

        content = source_content.strip()
        if not content:
            return ""

        max_chars = 12000
        if len(content) > max_chars:
            logger.info(f"网页参考内容过长（{len(content)} 字符），已截断到 {max_chars} 字符")
            content = content[:max_chars] + "\n\n...(网页正文过长，已截断)"

        return (
            "\n\n【网页参考素材】\n"
            "以下内容来自用户提供的网页正文，请优先吸收其中的关键观点、数据和案例，"
            "并在大纲中自然融合：\n\n"
            f"{content}"
        )

    def _build_template_reference(self, template_ref: Optional[Dict[str, Any]]) -> str:
        """构造模板参考片段：只参考布局和风格，不覆盖用户主题。"""
        if not template_ref or not isinstance(template_ref, dict):
            return ""

        title = str(template_ref.get("title", "")).strip()
        description = str(template_ref.get("description", "")).strip()
        style_prompt = str(
            template_ref.get("stylePrompt") or template_ref.get("style_prompt") or ""
        ).strip()

        if not any([title, description, style_prompt]):
            return ""

        return (
            "\n\n【模板参考（仅布局与风格）】\n"
            "用户已选择模板，请仅参考该模板的版式结构、视觉风格和表达节奏，"
            "不要替换或改写用户输入的主题。\n"
            f"- 模板名称: {title or '未提供'}\n"
            f"- 描述: {description or '未提供'}\n"
            f"- 风格提示: {style_prompt or '未提供'}\n"
        )

    def _pages_to_outline_text(self, pages: List[Dict[str, Any]]) -> str:
        """将页面数组序列化为统一的大纲文本格式。"""
        if not pages:
            return ""
        return "\n\n<page>\n\n".join(
            str(page.get("content", "")).strip()
            for page in pages
            if str(page.get("content", "")).strip()
        )

    def _extract_json_object(self, text: str) -> Optional[Dict[str, Any]]:
        """从模型返回文本中提取首个 JSON 对象。"""
        if not text:
            return None

        raw = text.strip()

        # 兼容 ```json ... ``` 包裹
        fenced_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw, flags=re.IGNORECASE)
        if fenced_match:
            raw = fenced_match.group(1).strip()

        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except Exception:
            pass

        # 回退：提取最外层大括号
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        snippet = raw[start:end + 1]
        try:
            data = json.loads(snippet)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _fallback_image_suggestion(
        self,
        page: Dict[str, Any],
        page_index: int,
        topic: str,
        style_hint: str
    ) -> str:
        """模型失败时的兜底配图建议。"""
        content = str(page.get("content", "")).strip()
        brief = re.sub(r"\s+", " ", content)[:60] if content else topic[:40]
        role = {
            "cover": "封面主视觉",
            "content": "内容信息表达",
            "summary": "总结收束页"
        }.get(str(page.get("type", "content")), "内容信息表达")

        base = (
            f"第{page_index + 1}页（{role}）：围绕“{brief}”构图；"
            "3:4竖版，整体保持同一主色调、同一光线方向与同一镜头语言，"
            "保证系列感与连续性。"
        )
        if style_hint:
            base += f" 风格锚点：{style_hint[:120]}"
        return base

    def _generate_image_suggestions(
        self,
        topic: str,
        pages: List[Dict[str, Any]],
        template_ref: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """调用模型为每一页生成配图建议。"""
        if not pages:
            return pages

        style_hint = ""
        if isinstance(template_ref, dict):
            style_hint = str(
                template_ref.get("stylePrompt")
                or template_ref.get("style_prompt")
                or template_ref.get("description")
                or ""
            ).strip()

        page_payload = []
        for page in pages:
            page_payload.append({
                "index": int(page.get("index", 0)),
                "type": str(page.get("type", "content")),
                "content": re.sub(r"\s+", " ", str(page.get("content", ""))).strip()[:220]
            })

        prompt = (
            "你是小红书图文编导，请为每一页生成“配图建议”。\n"
            "要求：\n"
            "1. 每页建议必须具体到主体、场景、构图、镜头/光线。\n"
            "2. 强调整组图片风格一致（统一色调、光线、镜头语言、氛围）。\n"
            "3. 中文输出，不要解释过程。\n"
            "4. 仅输出 JSON 对象，不要 Markdown 代码块。\n\n"
            f"主题：{topic}\n"
            f"风格锚点：{style_hint or '3:4竖版，小红书高质感，整组统一风格'}\n"
            f"页面数据：{json.dumps(page_payload, ensure_ascii=False)}\n\n"
            "输出格式：\n"
            "{\n"
            '  "suggestions": [\n'
            '    {"index": 0, "image_suggestion": "..."},\n'
            '    {"index": 1, "image_suggestion": "..."}\n'
            "  ]\n"
            "}\n"
        )

        try:
            client, provider_name, provider_config = self._get_client(needs_image_support=False)
            model = provider_config.get('model', 'gemini-2.0-flash-exp')
            temperature = provider_config.get('temperature', 0.7)
            max_output_tokens = provider_config.get('max_output_tokens', 6000)

            logger.info(
                f"调用配图建议生成: provider={provider_name}, model={model}, pages={len(pages)}"
            )

            raw = client.generate_text(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_output_tokens=max_output_tokens
            )

            data = self._extract_json_object(raw)
            suggestions = data.get("suggestions", []) if isinstance(data, dict) else []
            if not isinstance(suggestions, list):
                suggestions = []

            suggestion_map: Dict[int, str] = {}
            for item in suggestions:
                if not isinstance(item, dict):
                    continue
                index = item.get("index")
                text = item.get("image_suggestion")
                if isinstance(index, int) and isinstance(text, str) and text.strip():
                    suggestion_map[index] = text.strip()

            for idx, page in enumerate(pages):
                page["image_suggestion"] = suggestion_map.get(
                    idx,
                    self._fallback_image_suggestion(page, idx, topic, style_hint)
                )

            return pages

        except Exception as e:
            logger.warning(f"生成配图建议失败，使用兜底建议: {e}")
            for idx, page in enumerate(pages):
                page["image_suggestion"] = self._fallback_image_suggestion(
                    page, idx, topic, style_hint
                )
            return pages

    def _build_revision_prompt(
        self,
        topic: str,
        current_outline: str,
        revision_request: str,
        template_ref: Optional[Dict[str, Any]]
    ) -> str:
        """构建“修改需求重写大纲”提示词。"""
        outline_text = (current_outline or "").strip()
        if len(outline_text) > 14000:
            outline_text = outline_text[:14000] + "\n\n...(当前大纲过长，已截断)"

        prompt = self.prompt_template.format(topic=topic)
        prompt += self._build_template_reference(template_ref)
        prompt += (
            "\n\n【当前大纲】\n"
            f"{outline_text or '（为空）'}\n"
            "\n【修改需求】\n"
            f"{revision_request.strip()}\n"
            "\n【执行要求】\n"
            "请基于“修改需求”重写完整大纲，并保持清晰的页间逻辑与节奏。\n"
            "输出必须使用 <page> 作为页面分隔符；每页开头保留类型标记 [封面]/[内容]/[总结]。\n"
        )
        return prompt

    def edit_outline_with_suggestions(
        self,
        topic: str,
        current_outline: str,
        current_pages: Optional[List[Dict[str, Any]]] = None,
        revision_request: str = "",
        mode: str = "revise",
        template_ref: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        编辑大纲并生成每页配图建议。

        mode:
        - suggest_only: 不改文案，只补全配图建议
        - revise: 根据修改需求重写大纲并补全配图建议
        """
        normalized_mode = (mode or "revise").strip().lower()
        if normalized_mode not in {"suggest_only", "revise"}:
            normalized_mode = "revise"

        pages_input = current_pages or []
        pages_input = [p for p in pages_input if isinstance(p, dict)]
        for idx, p in enumerate(pages_input):
            clean_content, embedded_suggestion = self._extract_embedded_image_suggestion(
                str(p.get("content", "")).strip()
            )
            merged_suggestion = self._merge_suggestion(
                str(p.get("image_suggestion", "")).strip() or None,
                embedded_suggestion
            )
            p["index"] = idx
            p["type"] = str(p.get("type", "content"))
            p["content"] = clean_content
            p["image_suggestion"] = merged_suggestion

        if normalized_mode == "suggest_only":
            pages = pages_input if pages_input else self._parse_outline(current_outline or "")
            pages = self._generate_image_suggestions(topic, pages, template_ref)
            return {
                "success": True,
                "outline": current_outline or self._pages_to_outline_text(pages),
                "pages": pages,
                "mode": normalized_mode
            }

        if not revision_request.strip():
            return {
                "success": False,
                "error": "revision_request 不能为空（revise 模式）"
            }

        try:
            client, provider_name, provider_config = self._get_client(needs_image_support=False)
            model = provider_config.get('model', 'gemini-2.0-flash-exp')
            temperature = provider_config.get('temperature', 0.8)
            max_output_tokens = provider_config.get('max_output_tokens', 8000)

            prompt = self._build_revision_prompt(topic, current_outline, revision_request, template_ref)
            logger.info(
                f"开始重写大纲: provider={provider_name}, model={model}, revision_len={len(revision_request)}"
            )

            outline_text = client.generate_text(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_output_tokens=max_output_tokens
            )
            pages = self._parse_outline(outline_text)
            if not pages:
                return {
                    "success": False,
                    "error": "模型未返回可解析的大纲，请重试或调整修改需求"
                }

            pages = self._generate_image_suggestions(topic, pages, template_ref)

            return {
                "success": True,
                "outline": outline_text,
                "pages": pages,
                "mode": normalized_mode
            }

        except Exception as e:
            logger.error(f"编辑大纲失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def generate_outline(
        self,
        topic: str,
        images: Optional[List[bytes]] = None,
        source_content: Optional[str] = None,
        template_ref: Optional[Dict[str, Any]] = None,
        enable_search: bool = False,
    ) -> Dict[str, Any]:
        try:
            logger.info(
                "开始生成大纲: "
                f"topic={topic[:50]}..., "
                f"images={len(images) if images else 0}, "
                f"has_source={bool(source_content)}, "
                f"has_template_ref={bool(template_ref)}, "
                f"enable_search={enable_search}"
            )
            needs_image_support = bool(images and len(images) > 0)
            client, selected_provider_name, provider_config = self._get_client(
                needs_image_support=needs_image_support
            )
            prompt = self.prompt_template.format(topic=topic)
            prompt += self._build_source_reference(source_content)
            prompt += self._build_template_reference(template_ref)

            if images and len(images) > 0:
                prompt += f"\n\n注意：用户提供了 {len(images)} 张参考图片，请在生成大纲时考虑这些图片的内容和风格。这些图片可能是产品图、个人照片或场景图，请根据图片内容来优化大纲，使生成的内容与图片相关联。"
                logger.debug(f"添加了 {len(images)} 张参考图片到提示词")

            model = provider_config.get('model', 'gemini-2.0-flash-exp')
            temperature = provider_config.get('temperature', 1.0)
            max_output_tokens = provider_config.get('max_output_tokens', 8000)

            logger.info(
                f"调用文本生成 API: provider={selected_provider_name}, model={model}, "
                f"temperature={temperature}, needs_image_support={needs_image_support}"
            )
            outline_text = client.generate_text(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                images=images,
                use_search=enable_search
            )

            logger.debug(f"API 返回文本长度: {len(outline_text)} 字符")
            pages = self._parse_outline(outline_text)
            logger.info(f"大纲解析完成，共 {len(pages)} 页")

            return {
                "success": True,
                "outline": outline_text,
                "pages": pages,
                "has_images": images is not None and len(images) > 0
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"大纲生成失败: {error_msg}")

            # 根据错误类型提供更详细的错误信息
            if "api_key" in error_msg.lower() or "unauthorized" in error_msg.lower() or "401" in error_msg:
                detailed_error = (
                    f"API 认证失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. API Key 无效或已过期\n"
                    "2. API Key 没有访问该模型的权限\n"
                    "解决方案：在系统设置页面检查并更新 API Key"
                )
            elif "model" in error_msg.lower() or "404" in error_msg:
                detailed_error = (
                    f"模型访问失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. 模型名称不正确\n"
                    "2. 没有访问该模型的权限\n"
                    "解决方案：在系统设置页面检查模型名称配置"
                )
            elif "timeout" in error_msg.lower() or "连接" in error_msg:
                detailed_error = (
                    f"网络连接失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. 网络连接不稳定\n"
                    "2. API 服务暂时不可用\n"
                    "3. Base URL 配置错误\n"
                    "解决方案：检查网络连接，稍后重试"
                )
            elif "rate" in error_msg.lower() or "429" in error_msg or "quota" in error_msg.lower():
                detailed_error = (
                    f"API 配额限制。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. API 调用次数超限\n"
                    "2. 账户配额用尽\n"
                    "解决方案：等待配额重置，或升级 API 套餐"
                )
            else:
                detailed_error = (
                    f"大纲生成失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. Text API 配置错误或密钥无效\n"
                    "2. 网络连接问题\n"
                    "3. 模型无法访问或不存在\n"
                    "建议：检查配置文件 text_providers.yaml"
                )

            return {
                "success": False,
                "error": detailed_error
            }


def get_outline_service() -> OutlineService:
    """
    获取大纲生成服务实例
    每次调用都创建新实例以确保配置是最新的
    """
    return OutlineService()
