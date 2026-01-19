"""
概念可视化历史记录服务

负责管理概念可视化生成历史记录的存储、查询、更新和删除。
独立于小红书图文历史记录，使用独立的存储目录。

存储目录: history/concepts/
"""

import os
import json
import uuid
import logging
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class ConceptRecordStatus:
    """概念可视化记录状态常量"""
    DRAFT = "draft"           # 草稿：已创建，未完成
    IN_PROGRESS = "in_progress"  # 进行中：Pipeline 正在运行
    COMPLETED = "completed"   # 已完成：所有步骤完成
    ERROR = "error"           # 错误：生成过程中出现错误


class ConceptHistoryService:
    """概念可视化历史记录服务"""

    def __init__(self):
        """初始化概念历史记录服务"""
        # 项目根目录
        project_root = Path(__file__).parent.parent.parent

        # 概念历史记录存储目录
        self.history_dir = project_root / "history" / "concepts"
        self.history_dir.mkdir(parents=True, exist_ok=True)

        # 索引文件
        self.index_file = self.history_dir / "index.json"
        self._init_index()

        logger.info(f"概念历史服务初始化，存储目录: {self.history_dir}")

    def _init_index(self) -> None:
        """初始化索引文件"""
        if not self.index_file.exists():
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump({"records": []}, f, ensure_ascii=False, indent=2)

    def _load_index(self) -> Dict:
        """加载索引文件"""
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"records": []}

    def _save_index(self, index: Dict) -> None:
        """保存索引文件"""
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def _get_record_path(self, record_id: str) -> Path:
        """获取记录文件路径"""
        return self.history_dir / f"{record_id}.json"

    def create_record(
        self,
        title: str,
        article: str,
        task_id: str,
        style: Optional[str] = None
    ) -> str:
        """
        创建新的概念历史记录

        Args:
            title: 主题标题（从 analyze 结果提取，或默认取文章前20字）
            article: 原始文章内容
            task_id: Pipeline 任务 ID
            style: 可视化风格

        Returns:
            str: 新创建的记录 ID
        """
        record_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        # 文章预览（前200字）
        article_preview = article[:200] + "..." if len(article) > 200 else article

        # 创建完整记录
        record = {
            "id": record_id,
            "title": title or article[:20],
            "created_at": now,
            "updated_at": now,
            "status": ConceptRecordStatus.IN_PROGRESS,
            "task_id": task_id,
            "style": style,
            "article_preview": article_preview,
            "article_full": article,
            "thumbnail": None,
            "image_count": 0,
            "pipeline_data": {
                "analyze": None,
                "map": None,
                "design": None,
                "generate": None
            }
        }

        # 保存记录文件
        record_path = self._get_record_path(record_id)
        with open(record_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        # 更新索引
        index = self._load_index()
        index["records"].insert(0, {
            "id": record_id,
            "title": title or article[:20],
            "created_at": now,
            "updated_at": now,
            "status": ConceptRecordStatus.IN_PROGRESS,
            "task_id": task_id,
            "style": style,
            "article_preview": article_preview,
            "thumbnail": None,
            "image_count": 0
        })
        self._save_index(index)

        logger.info(f"创建概念历史记录: {record_id}")
        return record_id

    def get_record(self, record_id: str) -> Optional[Dict]:
        """
        获取历史记录详情

        Args:
            record_id: 记录 ID

        Returns:
            记录详情，不存在则返回 None
        """
        record_path = self._get_record_path(record_id)

        if not record_path.exists():
            return None

        try:
            with open(record_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取记录失败: {record_id}, {e}")
            return None

    def update_record(
        self,
        record_id: str,
        title: Optional[str] = None,
        status: Optional[str] = None,
        thumbnail: Optional[str] = None,
        image_count: Optional[int] = None,
        pipeline_data: Optional[Dict] = None
    ) -> bool:
        """
        更新历史记录

        Args:
            record_id: 记录 ID
            title: 标题（可选）
            status: 状态（可选）
            thumbnail: 缩略图路径（可选）
            image_count: 图片数量（可选）
            pipeline_data: Pipeline 数据，部分更新（可选）

        Returns:
            bool: 更新是否成功
        """
        record = self.get_record(record_id)
        if not record:
            return False

        now = datetime.now().isoformat()
        record["updated_at"] = now

        if title is not None:
            record["title"] = title
        if status is not None:
            record["status"] = status
        if thumbnail is not None:
            record["thumbnail"] = thumbnail
        if image_count is not None:
            record["image_count"] = image_count

        # 部分更新 pipeline_data
        if pipeline_data is not None:
            for key, value in pipeline_data.items():
                if key in record["pipeline_data"]:
                    record["pipeline_data"][key] = value

        # 保存记录
        record_path = self._get_record_path(record_id)
        with open(record_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        # 同步更新索引
        index = self._load_index()
        for idx_record in index["records"]:
            if idx_record["id"] == record_id:
                idx_record["updated_at"] = now
                if title is not None:
                    idx_record["title"] = title
                if status is not None:
                    idx_record["status"] = status
                if thumbnail is not None:
                    idx_record["thumbnail"] = thumbnail
                if image_count is not None:
                    idx_record["image_count"] = image_count
                break
        self._save_index(index)

        return True

    def delete_record(self, record_id: str) -> bool:
        """
        删除历史记录

        同时删除：
        1. 记录 JSON 文件
        2. 关联的图片目录 (output/concepts/{task_id})

        Args:
            record_id: 记录 ID

        Returns:
            bool: 删除是否成功
        """
        record = self.get_record(record_id)
        if not record:
            return False

        # 删除关联的图片目录
        if record.get("task_id"):
            task_id = record["task_id"]
            project_root = Path(__file__).parent.parent.parent
            task_dir = project_root / "output" / "concepts" / task_id
            if task_dir.exists() and task_dir.is_dir():
                try:
                    shutil.rmtree(task_dir)
                    logger.info(f"已删除图片目录: {task_dir}")
                except Exception as e:
                    logger.error(f"删除图片目录失败: {task_dir}, {e}")

        # 删除记录文件
        record_path = self._get_record_path(record_id)
        try:
            record_path.unlink()
        except Exception as e:
            logger.error(f"删除记录文件失败: {record_path}, {e}")
            return False

        # 从索引中移除
        index = self._load_index()
        index["records"] = [r for r in index["records"] if r["id"] != record_id]
        self._save_index(index)

        logger.info(f"删除概念历史记录: {record_id}")
        return True

    def list_records(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None
    ) -> Dict:
        """
        分页获取历史记录列表

        Args:
            page: 页码，从 1 开始
            page_size: 每页记录数
            status: 状态过滤（可选）

        Returns:
            Dict: 分页结果
        """
        index = self._load_index()
        records = index.get("records", [])

        # 按状态过滤
        if status:
            records = [r for r in records if r.get("status") == status]

        # 分页
        total = len(records)
        start = (page - 1) * page_size
        end = start + page_size
        page_records = records[start:end]

        return {
            "records": page_records,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0
        }

    def get_record_by_task_id(self, task_id: str) -> Optional[Dict]:
        """
        根据 task_id 获取记录

        Args:
            task_id: Pipeline 任务 ID

        Returns:
            记录详情，不存在则返回 None
        """
        index = self._load_index()
        for idx_record in index.get("records", []):
            if idx_record.get("task_id") == task_id:
                return self.get_record(idx_record["id"])
        return None

    def repair_record_images(self, record_id: str) -> bool:
        """
        修复记录的图片信息

        扫描输出目录，填充 image_count、thumbnail 和 pipeline_data.generate.results

        Args:
            record_id: 记录 ID

        Returns:
            bool: 修复是否成功
        """
        record = self.get_record(record_id)
        if not record:
            return False

        task_id = record.get("task_id")
        if not task_id:
            return False

        # 查找图片目录
        project_root = Path(__file__).parent.parent.parent
        task_dir = project_root / "output" / "concepts" / task_id

        if not task_dir.exists():
            logger.warning(f"图片目录不存在: {task_dir}")
            return False

        # 扫描 PNG 文件
        images = sorted([f.name for f in task_dir.glob("*.png")])
        if not images:
            logger.warning(f"目录中没有图片: {task_dir}")
            return False

        # 构建 generate.results
        results = []
        for img_name in images:
            results.append({
                "output_path": f"output/concepts/{task_id}/{img_name}",
                "filename": img_name
            })

        # 更新记录
        self.update_record(
            record_id,
            thumbnail=images[0],
            image_count=len(images),
            status=ConceptRecordStatus.COMPLETED,
            pipeline_data={"generate": {"results": results}}
        )

        logger.info(f"修复记录图片信息: {record_id}, 找到 {len(images)} 张图片")
        return True

    def repair_all_records(self) -> Dict:
        """
        修复所有缺失图片信息的记录

        Returns:
            Dict: 修复结果统计
        """
        index = self._load_index()
        repaired = 0
        failed = 0

        for idx_record in index.get("records", []):
            record_id = idx_record["id"]
            record = self.get_record(record_id)

            # 检查是否需要修复
            if record and record.get("image_count", 0) == 0 and record.get("task_id"):
                if self.repair_record_images(record_id):
                    repaired += 1
                else:
                    failed += 1

        return {"repaired": repaired, "failed": failed}


# 单例实例
_service_instance = None


def get_concept_history_service() -> ConceptHistoryService:
    """
    获取概念历史记录服务实例（单例模式）

    Returns:
        ConceptHistoryService: 服务实例
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = ConceptHistoryService()
    return _service_instance
