"""
历史记录服务

负责管理绘本生成历史记录的存储、查询、更新和删除。
支持草稿、生成中、完成等多种状态流转。

存储模式：
- local: 本地文件存储（默认）
- supabase: Supabase 云存储

通过环境变量 HISTORY_STORAGE_MODE 控制存储模式。
"""

import os
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)

# 存储模式常量
STORAGE_MODE_LOCAL = "local"
STORAGE_MODE_SUPABASE = "supabase"


class RecordStatus:
    """历史记录状态常量"""
    DRAFT = "draft"          # 草稿：已创建大纲，未开始生成
    GENERATING = "generating"  # 生成中：正在生成图片
    PARTIAL = "partial"       # 部分完成：有部分图片生成
    COMPLETED = "completed"   # 已完成：所有图片已生成
    ERROR = "error"          # 错误：生成过程中出现错误


class HistoryService:
    def __init__(self):
        """
        初始化历史记录服务

        根据 HISTORY_STORAGE_MODE 环境变量选择存储模式：
        - local: 本地文件存储（默认）
        - supabase: Supabase 云存储
        """
        # 存储模式（默认为本地）
        self.storage_mode = os.getenv("HISTORY_STORAGE_MODE", STORAGE_MODE_LOCAL)
        logger.info(f"历史记录服务初始化，存储模式: {self.storage_mode}")

        # 本地存储相关配置
        self.history_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "history"
        )

        if self.storage_mode == STORAGE_MODE_LOCAL:
            os.makedirs(self.history_dir, exist_ok=True)
            self.index_file = os.path.join(self.history_dir, "index.json")
            self._init_index()

    @property
    def is_supabase_mode(self) -> bool:
        """是否使用 Supabase 存储模式"""
        return self.storage_mode == STORAGE_MODE_SUPABASE

    def _init_index(self) -> None:
        """
        初始化索引文件

        如果索引文件不存在，则创建一个空索引
        """
        if not os.path.exists(self.index_file):
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump({"records": []}, f, ensure_ascii=False, indent=2)

    def _load_index(self) -> Dict:
        """
        加载索引文件

        Returns:
            Dict: 索引数据，包含 records 列表
        """
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"records": []}

    def _save_index(self, index: Dict) -> None:
        """
        保存索引文件

        Args:
            index: 索引数据
        """
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def _get_record_path(self, record_id: str) -> str:
        """
        获取历史记录文件路径

        Args:
            record_id: 记录 ID

        Returns:
            str: 记录文件的完整路径
        """
        return os.path.join(self.history_dir, f"{record_id}.json")

    def create_record(
        self,
        topic: str,
        outline: Dict,
        task_id: Optional[str] = None
    ) -> str:
        """
        创建新的历史记录

        初始状态为 draft（草稿），表示大纲已创建但尚未开始生成图片。

        Args:
            topic: 绘本主题/标题
            outline: 大纲内容，包含 pages 数组等信息
            task_id: 关联的生成任务 ID（可选）

        Returns:
            str: 新创建的记录 ID（UUID 格式）

        状态流转：
            新建 -> draft（草稿状态）
        """
        if self.is_supabase_mode:
            return self._create_record_supabase(topic, outline, task_id)
        return self._create_record_local(topic, outline, task_id)

    def _create_record_supabase(self, topic: str, outline: Dict, task_id: Optional[str]) -> str:
        """Supabase 模式：创建历史记录"""
        from backend.utils.supabase_client import create_history_record as sb_create

        page_count = len(outline.get("pages", []))
        result = sb_create(
            title=topic,
            topic=topic,
            task_id=task_id,
            outline=outline,
            images=[],
            thumbnail=None,
            status=RecordStatus.DRAFT,
            page_count=page_count
        )

        if result.get("success") and result.get("record"):
            record_id = result["record"].get("id")
            logger.info(f"Supabase 创建历史记录成功: {record_id}")
            return record_id
        else:
            error = result.get("error", "未知错误")
            logger.error(f"Supabase 创建历史记录失败: {error}")
            raise Exception(f"创建历史记录失败: {error}")

    def _create_record_local(self, topic: str, outline: Dict, task_id: Optional[str]) -> str:
        """本地模式：创建历史记录"""
        # 生成唯一记录 ID
        record_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        # 创建完整的记录对象
        record = {
            "id": record_id,
            "title": topic,
            "created_at": now,
            "updated_at": now,
            "outline": outline,  # 保存完整的大纲数据
            "images": {
                "task_id": task_id,
                "generated": []  # 初始无生成图片
            },
            "status": RecordStatus.DRAFT,  # 初始状态：草稿
            "thumbnail": None  # 初始无缩略图
        }

        # 保存完整记录到独立文件
        record_path = self._get_record_path(record_id)
        with open(record_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        # 更新索引（用于快速列表查询）
        index = self._load_index()
        index["records"].insert(0, {
            "id": record_id,
            "title": topic,
            "created_at": now,
            "updated_at": now,
            "status": RecordStatus.DRAFT,  # 索引中也记录状态
            "thumbnail": None,
            "page_count": len(outline.get("pages", [])),  # 预期页数
            "task_id": task_id
        })
        self._save_index(index)

        return record_id

    def get_record(self, record_id: str) -> Optional[Dict]:
        """
        获取历史记录详情

        Args:
            record_id: 记录 ID

        Returns:
            Optional[Dict]: 记录详情，如果不存在则返回 None

        返回数据包含：
            - id: 记录 ID
            - title: 标题
            - created_at: 创建时间
            - updated_at: 更新时间
            - outline: 大纲内容
            - images: 图片信息（task_id 和 generated 列表）
            - status: 当前状态
            - thumbnail: 缩略图文件名
        """
        if self.is_supabase_mode:
            return self._get_record_supabase(record_id)
        return self._get_record_local(record_id)

    def _get_record_supabase(self, record_id: str) -> Optional[Dict]:
        """Supabase 模式：获取历史记录"""
        from backend.utils.supabase_client import get_history_record as sb_get

        result = sb_get(record_id)
        if result.get("success") and result.get("record"):
            record = result["record"]
            # 转换格式以兼容本地模式
            return self._convert_supabase_record(record)
        return None

    def _get_record_local(self, record_id: str) -> Optional[Dict]:
        """本地模式：获取历史记录"""
        record_path = self._get_record_path(record_id)

        if not os.path.exists(record_path):
            return None

        try:
            with open(record_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _convert_supabase_record(self, record: Dict) -> Dict:
        """将 Supabase 记录格式转换为本地格式"""
        return {
            "id": record.get("id"),
            "title": record.get("title"),
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at"),
            "outline": record.get("outline", {}),
            "images": {
                "task_id": record.get("task_id"),
                "generated": record.get("images", [])
            },
            "status": record.get("status"),
            "thumbnail": record.get("thumbnail")
        }

    def record_exists(self, record_id: str) -> bool:
        """
        检查历史记录是否存在

        Args:
            record_id: 记录 ID

        Returns:
            bool: 记录是否存在
        """
        if self.is_supabase_mode:
            from backend.utils.supabase_client import get_history_record as sb_get
            result = sb_get(record_id)
            return result.get("success", False)
        record_path = self._get_record_path(record_id)
        return os.path.exists(record_path)

    def update_record(
        self,
        record_id: str,
        outline: Optional[Dict] = None,
        images: Optional[Dict] = None,
        status: Optional[str] = None,
        thumbnail: Optional[str] = None
    ) -> bool:
        """
        更新历史记录

        支持部分更新，只更新提供的字段。
        每次更新都会自动刷新 updated_at 时间戳。

        Args:
            record_id: 记录 ID
            outline: 大纲内容（可选，用于修改大纲）
            images: 图片信息（可选，包含 task_id 和 generated 列表）
            status: 状态（可选）
            thumbnail: 缩略图文件名（可选）

        Returns:
            bool: 更新是否成功，记录不存在时返回 False

        状态流转说明：
            draft -> generating: 开始生成图片
            generating -> partial: 部分图片生成完成
            generating -> completed: 所有图片生成完成
            generating -> error: 生成过程出错
            partial -> generating: 继续生成剩余图片
            partial -> completed: 剩余图片生成完成
        """
        if self.is_supabase_mode:
            return self._update_record_supabase(record_id, outline, images, status, thumbnail)
        return self._update_record_local(record_id, outline, images, status, thumbnail)

    def _update_record_supabase(
        self,
        record_id: str,
        outline: Optional[Dict] = None,
        images: Optional[Dict] = None,
        status: Optional[str] = None,
        thumbnail: Optional[str] = None
    ) -> bool:
        """Supabase 模式：更新历史记录"""
        from backend.utils.supabase_client import update_history_record as sb_update

        # 构建更新数据
        data = {}
        if outline is not None:
            data["outline"] = outline
            data["page_count"] = len(outline.get("pages", []))
        if images is not None:
            data["images"] = images.get("generated", [])
            if images.get("task_id"):
                data["task_id"] = images.get("task_id")
        if status is not None:
            data["status"] = status
        if thumbnail is not None:
            data["thumbnail"] = thumbnail

        if not data:
            return True  # 没有要更新的数据

        result = sb_update(record_id, data)
        return result.get("success", False)

    def _update_record_local(
        self,
        record_id: str,
        outline: Optional[Dict] = None,
        images: Optional[Dict] = None,
        status: Optional[str] = None,
        thumbnail: Optional[str] = None
    ) -> bool:
        """本地模式：更新历史记录"""
        # 获取现有记录
        record = self._get_record_local(record_id)
        if not record:
            return False

        # 更新时间戳
        now = datetime.now().isoformat()
        record["updated_at"] = now

        # 更新大纲内容（支持修改大纲）
        if outline is not None:
            record["outline"] = outline

        # 更新图片信息
        if images is not None:
            record["images"] = images

        # 更新状态（状态流转）
        if status is not None:
            record["status"] = status

        # 更新缩略图
        if thumbnail is not None:
            record["thumbnail"] = thumbnail

        # 保存完整记录
        record_path = self._get_record_path(record_id)
        with open(record_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        # 同步更新索引
        index = self._load_index()
        for idx_record in index["records"]:
            if idx_record["id"] == record_id:
                idx_record["updated_at"] = now

                # 更新状态
                if status:
                    idx_record["status"] = status

                # 更新缩略图
                if thumbnail:
                    idx_record["thumbnail"] = thumbnail

                # 更新页数（如果大纲被修改）
                if outline:
                    idx_record["page_count"] = len(outline.get("pages", []))

                # 更新任务 ID
                if images is not None and images.get("task_id"):
                    idx_record["task_id"] = images.get("task_id")

                break

        self._save_index(index)
        return True

    def delete_record(self, record_id: str) -> bool:
        """
        删除历史记录

        会同时删除：
        1. 记录 JSON 文件（本地模式）/ 数据库记录（Supabase 模式）
        2. 关联的任务图片目录（本地模式）/ Storage 图片（Supabase 模式）
        3. 索引中的记录（本地模式）

        Args:
            record_id: 记录 ID

        Returns:
            bool: 删除是否成功，记录不存在时返回 False
        """
        if self.is_supabase_mode:
            return self._delete_record_supabase(record_id)
        return self._delete_record_local(record_id)

    def _delete_record_supabase(self, record_id: str) -> bool:
        """Supabase 模式：删除历史记录"""
        from backend.utils.supabase_client import delete_history_record as sb_delete

        result = sb_delete(record_id)
        return result.get("success", False)

    def _delete_record_local(self, record_id: str) -> bool:
        """本地模式：删除历史记录"""
        record = self._get_record_local(record_id)
        if not record:
            return False

        # 删除关联的任务图片目录
        if record.get("images") and record["images"].get("task_id"):
            task_id = record["images"]["task_id"]
            task_dir = os.path.join(self.history_dir, task_id)
            if os.path.exists(task_dir) and os.path.isdir(task_dir):
                try:
                    import shutil
                    shutil.rmtree(task_dir)
                    logger.info(f"已删除任务目录: {task_dir}")
                except Exception as e:
                    logger.error(f"删除任务目录失败: {task_dir}, {e}")

        # 删除记录 JSON 文件
        record_path = self._get_record_path(record_id)
        try:
            os.remove(record_path)
        except Exception:
            return False

        # 从索引中移除
        index = self._load_index()
        index["records"] = [r for r in index["records"] if r["id"] != record_id]
        self._save_index(index)

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
            status: 状态过滤（可选），支持：draft/generating/partial/completed/error

        Returns:
            Dict: 分页结果
                - records: 当前页的记录列表
                - total: 总记录数
                - page: 当前页码
                - page_size: 每页大小
                - total_pages: 总页数
        """
        if self.is_supabase_mode:
            return self._list_records_supabase(page, page_size, status)
        return self._list_records_local(page, page_size, status)

    def _list_records_supabase(self, page: int, page_size: int, status: Optional[str]) -> Dict:
        """Supabase 模式：获取历史记录列表"""
        from backend.utils.supabase_client import list_history_records as sb_list

        result = sb_list(page, page_size, status)
        if result.get("success"):
            total = result.get("total", 0)
            return {
                "records": result.get("records", []),
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 0
            }
        return {
            "records": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0
        }

    def _list_records_local(self, page: int, page_size: int, status: Optional[str]) -> Dict:
        """本地模式：获取历史记录列表"""
        index = self._load_index()
        records = index.get("records", [])

        # 按状态过滤
        if status:
            records = [r for r in records if r.get("status") == status]

        # 分页计算
        total = len(records)
        start = (page - 1) * page_size
        end = start + page_size
        page_records = records[start:end]

        return {
            "records": page_records,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    def search_records(self, keyword: str) -> List[Dict]:
        """
        根据关键词搜索历史记录

        Args:
            keyword: 搜索关键词（不区分大小写）

        Returns:
            List[Dict]: 匹配的记录列表（按创建时间倒序）
        """
        if self.is_supabase_mode:
            return self._search_records_supabase(keyword)
        return self._search_records_local(keyword)

    def _search_records_supabase(self, keyword: str) -> List[Dict]:
        """Supabase 模式：搜索历史记录"""
        from backend.utils.supabase_client import search_history_records as sb_search

        result = sb_search(keyword)
        if result.get("success"):
            return result.get("records", [])
        return []

    def _search_records_local(self, keyword: str) -> List[Dict]:
        """本地模式：搜索历史记录"""
        index = self._load_index()
        records = index.get("records", [])

        # 不区分大小写的标题搜索
        keyword_lower = keyword.lower()
        results = [
            r for r in records
            if keyword_lower in r.get("title", "").lower()
        ]

        return results

    def get_statistics(self) -> Dict:
        """
        获取历史记录统计信息

        Returns:
            Dict: 统计数据
                - total: 总记录数
                - by_status: 各状态的记录数
                    - draft: 草稿数
                    - generating: 生成中数
                    - partial: 部分完成数
                    - completed: 已完成数
                    - error: 错误数
        """
        if self.is_supabase_mode:
            return self._get_statistics_supabase()
        return self._get_statistics_local()

    def _get_statistics_supabase(self) -> Dict:
        """Supabase 模式：获取统计信息"""
        from backend.utils.supabase_client import get_history_statistics as sb_stats

        result = sb_stats()
        if result.get("success"):
            return result.get("statistics", {"total": 0, "by_status": {}})
        return {"total": 0, "by_status": {}}

    def _get_statistics_local(self) -> Dict:
        """本地模式：获取统计信息"""
        index = self._load_index()
        records = index.get("records", [])

        total = len(records)
        status_count = {}

        # 统计各状态的记录数
        for record in records:
            status = record.get("status", RecordStatus.DRAFT)
            status_count[status] = status_count.get(status, 0) + 1

        return {
            "total": total,
            "by_status": status_count
        }

    def scan_and_sync_task_images(self, task_id: str) -> Dict[str, Any]:
        """
        扫描任务文件夹，同步图片列表

        根据实际生成的图片数量自动更新记录状态：
        - 无图片 -> draft（草稿）
        - 部分图片 -> partial（部分完成）
        - 全部图片 -> completed（已完成）

        Args:
            task_id: 任务 ID

        Returns:
            Dict[str, Any]: 扫描结果
                - success: 是否成功
                - record_id: 关联的记录 ID
                - task_id: 任务 ID
                - images_count: 图片数量
                - images: 图片文件名列表
                - status: 更新后的状态
                - error: 错误信息（失败时）
        """
        task_dir = os.path.join(self.history_dir, task_id)

        if not os.path.exists(task_dir) or not os.path.isdir(task_dir):
            return {
                "success": False,
                "error": f"任务目录不存在: {task_id}"
            }

        try:
            # 扫描目录下所有图片文件（排除缩略图）
            image_files = []
            for filename in os.listdir(task_dir):
                # 跳过缩略图文件（以 thumb_ 开头）
                if filename.startswith('thumb_'):
                    continue
                if filename.endswith('.png') or filename.endswith('.jpg') or filename.endswith('.jpeg'):
                    image_files.append(filename)

            # 按文件名排序（数字排序）
            def get_index(filename):
                try:
                    return int(filename.split('.')[0])
                except:
                    return 999

            image_files.sort(key=get_index)

            # 查找关联的历史记录
            index = self._load_index()
            record_id = None
            for rec in index.get("records", []):
                # 通过遍历所有记录，找到 task_id 匹配的记录
                record_detail = self.get_record(rec["id"])
                if record_detail and record_detail.get("images", {}).get("task_id") == task_id:
                    record_id = rec["id"]
                    break

            if record_id:
                # 更新历史记录
                record = self.get_record(record_id)
                if record:
                    # 根据生成图片数量判断状态
                    expected_count = len(record.get("outline", {}).get("pages", []))
                    actual_count = len(image_files)

                    if actual_count == 0:
                        status = RecordStatus.DRAFT  # 无图片：草稿
                    elif actual_count >= expected_count:
                        status = RecordStatus.COMPLETED  # 全部完成
                    else:
                        status = RecordStatus.PARTIAL  # 部分完成

                    # 更新图片列表和状态
                    self.update_record(
                        record_id,
                        images={
                            "task_id": task_id,
                            "generated": image_files
                        },
                        status=status,
                        thumbnail=image_files[0] if image_files else None
                    )

                    return {
                        "success": True,
                        "record_id": record_id,
                        "task_id": task_id,
                        "images_count": len(image_files),
                        "images": image_files,
                        "status": status
                    }

            # 没有关联的记录，返回扫描结果
            return {
                "success": True,
                "task_id": task_id,
                "images_count": len(image_files),
                "images": image_files,
                "no_record": True
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"扫描任务失败: {str(e)}"
            }

    def scan_all_tasks(self) -> Dict[str, Any]:
        """
        扫描所有任务文件夹，同步图片列表

        批量扫描 history 目录下的所有任务文件夹，
        同步图片列表并更新记录状态。

        Returns:
            Dict[str, Any]: 扫描结果统计
                - success: 是否成功
                - total_tasks: 扫描的任务总数
                - synced: 成功同步的任务数
                - failed: 失败的任务数
                - orphan_tasks: 孤立任务列表（有图片但无记录）
                - results: 详细结果列表
                - error: 错误信息（失败时）
        """
        if not os.path.exists(self.history_dir):
            return {
                "success": False,
                "error": "历史记录目录不存在"
            }

        try:
            synced_count = 0
            failed_count = 0
            orphan_tasks = []  # 没有关联记录的任务
            results = []

            # 遍历 history 目录
            for item in os.listdir(self.history_dir):
                item_path = os.path.join(self.history_dir, item)

                # 只处理目录（任务文件夹）
                if not os.path.isdir(item_path):
                    continue

                # 假设任务文件夹名就是 task_id
                task_id = item

                # 扫描并同步
                result = self.scan_and_sync_task_images(task_id)
                results.append(result)

                if result.get("success"):
                    if result.get("no_record"):
                        orphan_tasks.append(task_id)
                    else:
                        synced_count += 1
                else:
                    failed_count += 1

            return {
                "success": True,
                "total_tasks": len(results),
                "synced": synced_count,
                "failed": failed_count,
                "orphan_tasks": orphan_tasks,
                "results": results
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"扫描所有任务失败: {str(e)}"
            }


_service_instance = None


def get_history_service() -> HistoryService:
    """
    获取历史记录服务实例（单例模式）

    Returns:
        HistoryService: 历史记录服务实例
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = HistoryService()
    return _service_instance
