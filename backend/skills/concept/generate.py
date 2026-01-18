"""
ConceptGenerateSkill - 概念图图像生成

根据设计方案生成概念可视化图像
"""

import json
import time
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Union, List, Dict, Optional, Generator

from backend.core.base_skill import BaseSkill, SkillResult
from backend.clients.factory import ClientFactory
from backend.knowledge import registry

logger = logging.getLogger(__name__)


@dataclass
class GenerateInput:
    """生成技能输入"""
    designs: Union[List[Dict], Dict]  # design 结果或设计列表
    style: str = "blueprint"  # 视觉风格
    output_dir: str = "output/concepts"  # 输出目录


class ConceptGenerateSkill(BaseSkill):
    """概念图图像生成技能"""

    name = "concept_generate"
    description = "生成概念可视化图像"

    # 生成配置
    REQUEST_DELAY = 2.0  # 请求间隔（秒）

    def __init__(self, config=None, style: str = "blueprint"):
        super().__init__(config)
        self.style_id = style
        self._image_client = None
        self._style_prefix = None

    @property
    def image_client(self):
        """延迟加载图像生成客户端"""
        if self._image_client is None:
            provider_config = self.config.get('image_provider', {})
            if not provider_config:
                from backend.config import Config
                provider_name = Config.get_active_image_provider()
                provider_config = Config.get_image_provider_config(provider_name)
            self._image_client = ClientFactory.create_image_client(provider_config)
        return self._image_client

    @property
    def style_prefix(self) -> str:
        """获取统一样式前缀"""
        if self._style_prefix is None:
            style = registry.get_visual_style(self.style_id)
            self._style_prefix = style.get("style_prefix", style.get("template", ""))
        return self._style_prefix

    def run(self, input_data: GenerateInput) -> SkillResult:
        """
        批量生成概念图

        Args:
            input_data: 包含设计方案的输入

        Returns:
            包含生成结果的 SkillResult
        """
        designs = input_data.designs
        self.style_id = input_data.style or "blueprint"
        self._style_prefix = None  # 重置样式前缀

        # 处理输入
        if isinstance(designs, dict):
            if "designs" in designs:
                designs = designs["designs"]

        if isinstance(designs, str):
            designs = json.loads(designs)

        # 创建输出目录
        output_dir = Path(input_data.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = []
        total = len(designs)
        success_count = 0

        logger.info(f"开始批量生成 {total} 张概念图...")

        for i, design in enumerate(designs, 1):
            # 提取提示词和标题
            if isinstance(design, dict):
                prompt = design.get("image_prompt") or design.get("prompt")
                title = design.get("title", f"concept_{i:02d}")
                concept_id = design.get("concept_id", f"c{i}")
            else:
                prompt = design
                title = f"concept_{i:02d}"
                concept_id = f"c{i}"

            if not prompt:
                results.append({
                    "index": i,
                    "title": title,
                    "success": False,
                    "error": "缺少图像提示词"
                })
                continue

            # 清理文件名
            safe_title = "".join(c if c.isalnum() or c in "._-" else "_" for c in title)
            output_name = f"{i:02d}_{safe_title}"

            logger.info(f"[{i}/{total}] 生成: {title}")

            result = self._generate_single(
                prompt=prompt,
                output_dir=output_dir,
                output_name=output_name
            )

            result["index"] = i
            result["title"] = title
            result["concept_id"] = concept_id
            results.append(result)

            if result.get("success"):
                success_count += 1

            # 请求间隔
            if i < total:
                time.sleep(self.REQUEST_DELAY)

        logger.info(f"批量生成完成: {success_count}/{total} 成功")

        return SkillResult(
            success=success_count > 0,
            data={
                "results": results,
                "total": total,
                "success_count": success_count
            },
            message=f"完成 {success_count}/{total} 张概念图生成"
        )

    def run_stream(self, input_data: GenerateInput) -> Generator[Dict, None, None]:
        """
        流式生成概念图（用于 SSE）

        Args:
            input_data: 包含设计方案的输入

        Yields:
            每张图的生成进度和结果
        """
        designs = input_data.designs
        self.style_id = input_data.style or "blueprint"
        self._style_prefix = None

        if isinstance(designs, dict):
            if "designs" in designs:
                designs = designs["designs"]

        if isinstance(designs, str):
            designs = json.loads(designs)

        output_dir = Path(input_data.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        total = len(designs)
        success_count = 0

        yield {
            "type": "start",
            "total": total,
            "message": f"开始生成 {total} 张概念图"
        }

        for i, design in enumerate(designs, 1):
            if isinstance(design, dict):
                prompt = design.get("image_prompt") or design.get("prompt")
                title = design.get("title", f"concept_{i:02d}")
                concept_id = design.get("concept_id", f"c{i}")
            else:
                prompt = design
                title = f"concept_{i:02d}"
                concept_id = f"c{i}"

            yield {
                "type": "progress",
                "index": i,
                "total": total,
                "title": title,
                "status": "generating"
            }

            if not prompt:
                yield {
                    "type": "result",
                    "index": i,
                    "title": title,
                    "success": False,
                    "error": "缺少图像提示词"
                }
                continue

            safe_title = "".join(c if c.isalnum() or c in "._-" else "_" for c in title)
            output_name = f"{i:02d}_{safe_title}"

            result = self._generate_single(
                prompt=prompt,
                output_dir=output_dir,
                output_name=output_name
            )

            result["index"] = i
            result["title"] = title
            result["concept_id"] = concept_id

            if result.get("success"):
                success_count += 1

            yield {
                "type": "result",
                **result
            }

            if i < total:
                time.sleep(self.REQUEST_DELAY)

        yield {
            "type": "complete",
            "total": total,
            "success_count": success_count,
            "message": f"完成 {success_count}/{total} 张概念图"
        }

    def _generate_single(
        self,
        prompt: str,
        output_dir: Path,
        output_name: str
    ) -> Dict:
        """
        生成单张图像

        Args:
            prompt: 图像提示词
            output_dir: 输出目录
            output_name: 输出文件名（不含扩展名）

        Returns:
            生成结果字典
        """
        output_path = output_dir / f"{output_name}.png"

        # 添加统一样式前缀
        if self.style_prefix:
            full_prompt = f"{self.style_prefix}\n\n=== IMAGE CONTENT ===\n{prompt}"
        else:
            full_prompt = prompt

        try:
            # generate_image 返回 bytes
            image_data = self.image_client.generate_image(full_prompt)

            if image_data and isinstance(image_data, bytes):
                # 保存图片到文件
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(image_data)

                logger.info(f"图像已保存: {output_path}")
                return {
                    "success": True,
                    "output_path": str(output_path),
                    "url": None
                }
            else:
                logger.error(f"生成失败: 返回数据无效")
                return {
                    "success": False,
                    "error": "生成返回数据无效"
                }

        except Exception as e:
            logger.error(f"生成异常: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def format_output(self, result: SkillResult) -> str:
        """格式化输出结果"""
        if not result.success:
            return f"生成失败: {result.error}"

        data = result.data
        lines = [
            "# 概念图生成结果",
            "",
            f"成功: {data.get('success_count')}/{data.get('total')}",
            ""
        ]

        for r in data.get('results', []):
            status = "OK" if r.get("success") else "FAIL"
            path = r.get("output_path", r.get("error", "N/A"))
            lines.append(f"[{status}] {r.get('index')}. {r.get('title')}: {path}")

        return "\n".join(lines)
