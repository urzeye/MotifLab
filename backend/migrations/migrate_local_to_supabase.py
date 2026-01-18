#!/usr/bin/env python3
"""
数据迁移脚本：从本地文件存储迁移到 Supabase

使用方法：
1. 确保 Supabase 配置正确（检查 backend/utils/supabase_client.py）
2. 确保已在 Supabase Dashboard 中：
   - 执行 create_history_records.sql 创建数据库表
   - 创建 Storage bucket "renderink-images" 并设为 public
3. 运行: python -m backend.migrations.migrate_local_to_supabase

注意：
- 迁移过程中不会删除本地数据
- 如果记录已存在（通过 task_id 判断），将跳过
- 建议在迁移前备份 history/ 目录
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.utils.supabase_client import (
    create_history_record,
    get_history_record_by_task_id,
    upload_image,
    SUPABASE_URL,
    SUPABASE_KEY
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def load_local_index(history_dir: Path) -> List[Dict]:
    """加载本地索引文件"""
    index_file = history_dir / "index.json"
    if not index_file.exists():
        logger.warning(f"索引文件不存在: {index_file}")
        return []

    with open(index_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("records", [])


def load_local_record(history_dir: Path, record_id: str) -> Optional[Dict]:
    """加载本地完整记录"""
    record_file = history_dir / f"{record_id}.json"
    if not record_file.exists():
        logger.warning(f"记录文件不存在: {record_file}")
        return None

    with open(record_file, "r", encoding="utf-8") as f:
        return json.load(f)


def migrate_images(history_dir: Path, task_id: str) -> List[str]:
    """迁移任务目录下的图片到 Supabase Storage"""
    task_dir = history_dir / task_id
    if not task_dir.exists() or not task_dir.is_dir():
        logger.warning(f"任务目录不存在: {task_dir}")
        return []

    uploaded_images = []
    for filename in sorted(os.listdir(task_dir)):
        if not filename.endswith(('.png', '.jpg', '.jpeg')):
            continue

        filepath = task_dir / filename
        try:
            with open(filepath, "rb") as f:
                image_data = f.read()

            url = upload_image(task_id, filename, image_data)
            if url:
                uploaded_images.append(filename)
                logger.debug(f"  上传成功: {filename}")
            else:
                logger.error(f"  上传失败: {filename}")
        except Exception as e:
            logger.error(f"  上传异常: {filename}, 错误: {e}")

    return uploaded_images


def migrate_record(history_dir: Path, index_record: Dict) -> bool:
    """迁移单条记录"""
    record_id = index_record.get("id")
    task_id = index_record.get("task_id")

    logger.info(f"处理记录: {record_id[:8]}... (task: {task_id})")

    # 检查是否已存在
    if task_id:
        existing = get_history_record_by_task_id(task_id)
        if existing.get("success"):
            logger.info(f"  记录已存在，跳过")
            return True

    # 加载完整记录
    record = load_local_record(history_dir, record_id)
    if not record:
        logger.error(f"  无法加载记录文件")
        return False

    # 提取数据
    title = record.get("title", "")
    outline = record.get("outline", {})
    images_info = record.get("images", {})
    task_id = images_info.get("task_id") or task_id
    generated_images = images_info.get("generated", [])
    status = record.get("status", "draft")
    thumbnail = record.get("thumbnail")
    page_count = len(outline.get("pages", []))

    # 上传图片到 Storage
    if task_id and generated_images:
        logger.info(f"  上传图片: {len(generated_images)} 个文件")
        uploaded = migrate_images(history_dir, task_id)
        logger.info(f"  上传完成: {len(uploaded)} 个文件")

    # 创建数据库记录
    result = create_history_record(
        title=title,
        topic=title,
        task_id=task_id,
        outline=outline,
        images=generated_images,
        thumbnail=thumbnail,
        status=status,
        page_count=page_count
    )

    if result.get("success"):
        logger.info(f"  数据库记录创建成功")
        return True
    else:
        logger.error(f"  数据库记录创建失败: {result.get('error')}")
        return False


def main():
    """主迁移流程"""
    logger.info("=" * 60)
    logger.info("RenderInk 数据迁移：本地 → Supabase")
    logger.info("=" * 60)

    # 验证 Supabase 配置
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Supabase 配置缺失，请检查环境变量")
        sys.exit(1)

    logger.info(f"Supabase URL: {SUPABASE_URL}")
    logger.info("")

    # 查找 history 目录
    history_dir = project_root / "history"
    if not history_dir.exists():
        logger.error(f"history 目录不存在: {history_dir}")
        sys.exit(1)

    logger.info(f"本地 history 目录: {history_dir}")

    # 加载本地索引
    records = load_local_index(history_dir)
    logger.info(f"找到 {len(records)} 条本地记录")
    logger.info("")

    if not records:
        logger.info("没有需要迁移的记录")
        return

    # 确认迁移
    confirm = input(f"确认迁移 {len(records)} 条记录? (y/N): ")
    if confirm.lower() != 'y':
        logger.info("迁移已取消")
        return

    logger.info("")
    logger.info("开始迁移...")
    logger.info("-" * 60)

    # 迁移每条记录
    success_count = 0
    fail_count = 0

    for i, record in enumerate(records, 1):
        logger.info(f"[{i}/{len(records)}]")
        if migrate_record(history_dir, record):
            success_count += 1
        else:
            fail_count += 1
        logger.info("")

    # 输出统计
    logger.info("-" * 60)
    logger.info("迁移完成！")
    logger.info(f"  成功: {success_count}")
    logger.info(f"  失败: {fail_count}")
    logger.info("")
    logger.info("下一步：")
    logger.info("  1. 验证数据: 在 Supabase Dashboard 检查 history_records 表")
    logger.info("  2. 验证图片: 在 Storage 页面检查 renderink-images bucket")
    logger.info("  3. 切换模式: 设置环境变量 HISTORY_STORAGE_MODE=supabase")
    logger.info("  4. 重启服务: python -m backend.app")


if __name__ == "__main__":
    main()
