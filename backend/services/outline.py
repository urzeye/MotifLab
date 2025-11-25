import os
import re
import base64
from typing import Dict, List, Any, Optional
from backend.utils.text_client import get_text_chat_client


class OutlineService:
    def __init__(self):
        self.client = get_text_chat_client()
        self.prompt_template = self._load_prompt_template()

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

            pages.append({
                "index": index,
                "type": page_type,
                "content": page_text
            })

        return pages

    def generate_outline(
        self,
        topic: str,
        images: Optional[List[bytes]] = None
    ) -> Dict[str, Any]:
        try:
            prompt = self.prompt_template.format(topic=topic)

            if images and len(images) > 0:
                prompt += f"\n\n注意：用户提供了 {len(images)} 张参考图片，请在生成大纲时考虑这些图片的内容和风格。这些图片可能是产品图、个人照片或场景图，请根据图片内容来优化大纲，使生成的内容与图片相关联。"

            outline_text = self.client.generate_text(
                prompt=prompt,
                model="gemini-3-pro-preview",
                temperature=1.0,
                max_output_tokens=65535,
                images=images
            )

            pages = self._parse_outline(outline_text)

            return {
                "success": True,
                "outline": outline_text,
                "pages": pages,
                "has_images": images is not None and len(images) > 0
            }

        except Exception as e:
            error_msg = str(e)
            return {
                "success": False,
                "error": f"大纲生成失败。\n错误详情: {error_msg}\n可能原因：\n1. Text API配置错误或密钥无效\n2. 网络连接问题\n3. 模型无法访问或不存在\n4. 提示词格式有问题\n建议：检查 TEXT_API_KEY 环境变量配置和网络连接"
            }


_service_instance = None

def get_outline_service() -> OutlineService:
    global _service_instance
    if _service_instance is None:
        _service_instance = OutlineService()
    return _service_instance
