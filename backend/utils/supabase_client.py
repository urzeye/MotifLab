"""
Supabase 客户端

用于与 Supabase 数据库交互，存储发布记录等数据。
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Supabase 配置（从 .env 环境变量读取）
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

_supabase_client = None


def get_supabase_client():
    """获取 Supabase 客户端实例"""
    global _supabase_client
    if _supabase_client is None:
        try:
            from supabase import create_client
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Supabase 客户端初始化成功")
        except ImportError:
            logger.warning("supabase-py 未安装，使用 REST API 模式")
            _supabase_client = SupabaseRestClient(SUPABASE_URL, SUPABASE_KEY)
        except Exception as e:
            logger.error(f"Supabase 客户端初始化失败: {e}")
            _supabase_client = SupabaseRestClient(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client


class SupabaseRestClient:
    """使用 REST API 的 Supabase 客户端（备用方案）"""

    def __init__(self, url: str, key: str):
        self.url = url.rstrip('/')
        self.key = key
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    def table(self, name: str):
        return SupabaseTable(self, name)


class SupabaseTable:
    """Supabase 表操作类"""

    def __init__(self, client: SupabaseRestClient, table_name: str):
        self.client = client
        self.table_name = table_name
        self.base_url = f"{client.url}/rest/v1/{table_name}"

    def insert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """插入数据"""
        import requests
        response = requests.post(
            self.base_url,
            headers=self.client.headers,
            json=data
        )
        response.raise_for_status()
        result = response.json()
        return result[0] if isinstance(result, list) and result else result

    def select(self, columns: str = "*") -> 'SupabaseQuery':
        """查询数据"""
        return SupabaseQuery(self, columns)

    def update(self, data: Dict[str, Any]) -> 'SupabaseQuery':
        """更新数据"""
        return SupabaseQuery(self, "*", "PATCH", data)

    def delete(self) -> 'SupabaseQuery':
        """删除数据"""
        return SupabaseQuery(self, "*", "DELETE")


class SupabaseQuery:
    """Supabase 查询构建器"""

    def __init__(self, table: SupabaseTable, columns: str = "*", method: str = "GET", data: Dict = None):
        self.table = table
        self.columns = columns
        self.method = method
        self.data = data
        self.filters = []
        self._order = None
        self._limit = None

    def eq(self, column: str, value: Any) -> 'SupabaseQuery':
        """等于条件"""
        self.filters.append(f"{column}=eq.{value}")
        return self

    def order(self, column: str, desc: bool = False) -> 'SupabaseQuery':
        """排序"""
        self._order = f"{column}.{'desc' if desc else 'asc'}"
        return self

    def limit(self, count: int) -> 'SupabaseQuery':
        """限制返回数量"""
        self._limit = count
        return self

    def execute(self) -> Dict[str, Any]:
        """执行查询"""
        import requests

        url = f"{self.table.base_url}?select={self.columns}"

        if self.filters:
            url += "&" + "&".join(self.filters)
        if self._order:
            url += f"&order={self._order}"
        if self._limit:
            url += f"&limit={self._limit}"

        if self.method == "GET":
            response = requests.get(url, headers=self.table.client.headers)
        elif self.method == "PATCH":
            response = requests.patch(url, headers=self.table.client.headers, json=self.data)
        elif self.method == "DELETE":
            response = requests.delete(url, headers=self.table.client.headers)
        else:
            raise ValueError(f"不支持的方法: {self.method}")

        response.raise_for_status()
        return {"data": response.json(), "error": None}


# ==================== 发布记录操作 ====================

def create_publish_record(
    title: str,
    content: str,
    tags: List[str],
    images: List[Dict[str, Any]],
    project_id: Optional[str] = None
) -> Dict[str, Any]:
    """创建发布记录"""
    client = get_supabase_client()

    data = {
        "title": title,
        "content": content,
        "tags": tags,
        "images": images,
        "status": "draft",
        "project_id": project_id
    }

    try:
        result = client.table("xiaohongshu_posts").insert(data).execute()
        record = result.data[0] if result.data else {}
        logger.info(f"创建发布记录成功: {record.get('id', 'unknown')}")
        return {"success": True, "record": record}
    except Exception as e:
        logger.error(f"创建发布记录失败: {e}")
        return {"success": False, "error": str(e)}


def update_publish_status(
    record_id: str,
    status: str,
    post_url: Optional[str] = None,
    error: Optional[str] = None
) -> Dict[str, Any]:
    """更新发布状态"""
    client = get_supabase_client()

    data = {"status": status}
    if post_url:
        data["post_url"] = post_url
        data["published_at"] = datetime.utcnow().isoformat()
    if error:
        data["error"] = error

    try:
        result = client.table("xiaohongshu_posts").update(data).eq("id", record_id).execute()
        logger.info(f"更新发布状态成功: {record_id} -> {status}")
        return {"success": True, "record": result.data if result.data else []}
    except Exception as e:
        logger.error(f"更新发布状态失败: {e}")
        return {"success": False, "error": str(e)}


def get_publish_records(
    status: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """获取发布记录列表"""
    client = get_supabase_client()

    try:
        query = client.table("xiaohongshu_posts").select("*")
        if status:
            query = query.eq("status", status)
        query = query.order("created_at", desc=True).limit(limit)

        result = query.execute()
        return {"success": True, "records": result.data if result.data else []}
    except Exception as e:
        logger.error(f"获取发布记录失败: {e}")
        return {"success": False, "error": str(e), "records": []}


def get_publish_record(record_id: str) -> Dict[str, Any]:
    """获取单条发布记录"""
    client = get_supabase_client()

    try:
        result = client.table("xiaohongshu_posts").select("*").eq("id", record_id).execute()
        records = result.data if result.data else []
        if records:
            return {"success": True, "record": records[0]}
        return {"success": False, "error": "记录不存在"}
    except Exception as e:
        logger.error(f"获取发布记录失败: {e}")
        return {"success": False, "error": str(e)}


# ==================== Storage 操作 ====================

STORAGE_BUCKET = "renderink-images"


def upload_image(task_id: str, filename: str, data: bytes, content_type: str = "image/png") -> Optional[str]:
    """
    上传图片到 Supabase Storage

    Args:
        task_id: 任务 ID
        filename: 文件名 (如 "0.png", "thumb_0.png")
        data: 图片二进制数据
        content_type: MIME 类型

    Returns:
        成功返回公开 URL，失败返回 None
    """
    import requests

    path = f"{task_id}/{filename}"
    url = f"{SUPABASE_URL}/storage/v1/object/{STORAGE_BUCKET}/{path}"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": content_type,
        "x-upsert": "true"  # 如果文件存在则覆盖
    }

    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        public_url = get_image_url(task_id, filename)
        logger.debug(f"图片上传成功: {path}")
        return public_url
    except Exception as e:
        logger.error(f"图片上传失败: {path}, 错误: {e}")
        return None


def delete_image(task_id: str, filename: str) -> bool:
    """
    从 Supabase Storage 删除图片

    Args:
        task_id: 任务 ID
        filename: 文件名

    Returns:
        是否成功
    """
    import requests

    path = f"{task_id}/{filename}"
    url = f"{SUPABASE_URL}/storage/v1/object/{STORAGE_BUCKET}/{path}"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    try:
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        logger.debug(f"图片删除成功: {path}")
        return True
    except Exception as e:
        logger.error(f"图片删除失败: {path}, 错误: {e}")
        return False


def delete_task_images(task_id: str) -> bool:
    """
    删除任务下的所有图片

    Args:
        task_id: 任务 ID

    Returns:
        是否成功
    """
    import requests

    # 列出该任务目录下的所有文件
    list_url = f"{SUPABASE_URL}/storage/v1/object/list/{STORAGE_BUCKET}"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            list_url,
            headers=headers,
            json={"prefix": f"{task_id}/"}
        )
        response.raise_for_status()
        files = response.json()

        # 批量删除
        if files:
            paths = [f"{task_id}/{f['name']}" for f in files]
            delete_url = f"{SUPABASE_URL}/storage/v1/object/{STORAGE_BUCKET}"
            response = requests.delete(
                delete_url,
                headers=headers,
                json={"prefixes": paths}
            )
            response.raise_for_status()

        logger.info(f"删除任务图片成功: {task_id}, 共 {len(files)} 个文件")
        return True
    except Exception as e:
        logger.error(f"删除任务图片失败: {task_id}, 错误: {e}")
        return False


def get_image_url(task_id: str, filename: str) -> str:
    """
    获取图片的公开 URL

    Args:
        task_id: 任务 ID
        filename: 文件名

    Returns:
        公开 URL
    """
    return f"{SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{task_id}/{filename}"


# ==================== 历史记录操作 ====================

def create_history_record(
    title: str,
    topic: Optional[str] = None,
    task_id: Optional[str] = None,
    outline: Optional[Dict] = None,
    images: Optional[List[str]] = None,
    thumbnail: Optional[str] = None,
    status: str = "draft",
    page_count: int = 0
) -> Dict[str, Any]:
    """
    创建历史记录

    Args:
        title: 标题
        topic: 原始主题
        task_id: 任务 ID
        outline: 大纲数据
        images: 图片文件名列表
        thumbnail: 缩略图文件名
        status: 状态
        page_count: 页面数量

    Returns:
        {"success": bool, "record": dict} 或 {"success": bool, "error": str}
    """
    client = get_supabase_client()

    data = {
        "title": title,
        "topic": topic,
        "task_id": task_id,
        "outline": outline or {},
        "images": images or [],
        "thumbnail": thumbnail,
        "status": status,
        "page_count": page_count
    }

    try:
        result = client.table("history_records").insert(data).execute()
        record = result.data[0] if result.data else {}
        logger.info(f"创建历史记录成功: {record.get('id', 'unknown')}")
        return {"success": True, "record": record}
    except Exception as e:
        logger.error(f"创建历史记录失败: {e}")
        return {"success": False, "error": str(e)}


def get_history_record(record_id: str) -> Dict[str, Any]:
    """
    获取单条历史记录

    Args:
        record_id: 记录 ID

    Returns:
        {"success": bool, "record": dict} 或 {"success": bool, "error": str}
    """
    client = get_supabase_client()

    try:
        result = client.table("history_records").select("*").eq("id", record_id).execute()
        records = result.data if result.data else []
        if records:
            return {"success": True, "record": records[0]}
        return {"success": False, "error": "记录不存在"}
    except Exception as e:
        logger.error(f"获取历史记录失败: {e}")
        return {"success": False, "error": str(e)}


def get_history_record_by_task_id(task_id: str) -> Dict[str, Any]:
    """
    通过任务 ID 获取历史记录

    Args:
        task_id: 任务 ID

    Returns:
        {"success": bool, "record": dict} 或 {"success": bool, "error": str}
    """
    client = get_supabase_client()

    try:
        result = client.table("history_records").select("*").eq("task_id", task_id).execute()
        records = result.data if result.data else []
        if records:
            return {"success": True, "record": records[0]}
        return {"success": False, "error": "记录不存在"}
    except Exception as e:
        logger.error(f"获取历史记录失败: {e}")
        return {"success": False, "error": str(e)}


def update_history_record(record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    更新历史记录

    Args:
        record_id: 记录 ID
        data: 要更新的字段

    Returns:
        {"success": bool, "record": dict} 或 {"success": bool, "error": str}
    """
    client = get_supabase_client()

    try:
        result = client.table("history_records").update(data).eq("id", record_id).execute()
        records = result.data if result.data else []
        if records:
            logger.info(f"更新历史记录成功: {record_id}")
            return {"success": True, "record": records[0]}
        return {"success": False, "error": "记录不存在或更新失败"}
    except Exception as e:
        logger.error(f"更新历史记录失败: {e}")
        return {"success": False, "error": str(e)}


def delete_history_record(record_id: str) -> Dict[str, Any]:
    """
    删除历史记录

    Args:
        record_id: 记录 ID

    Returns:
        {"success": bool} 或 {"success": bool, "error": str}
    """
    client = get_supabase_client()

    try:
        # 先获取记录以获取 task_id
        record_result = get_history_record(record_id)
        if record_result.get("success") and record_result.get("record"):
            task_id = record_result["record"].get("task_id")
            if task_id:
                # 删除 Storage 中的图片
                delete_task_images(task_id)

        # 删除数据库记录
        client.table("history_records").delete().eq("id", record_id).execute()
        logger.info(f"删除历史记录成功: {record_id}")
        return {"success": True}
    except Exception as e:
        logger.error(f"删除历史记录失败: {e}")
        return {"success": False, "error": str(e)}


def list_history_records(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """
    获取历史记录列表

    Args:
        page: 页码 (从 1 开始)
        page_size: 每页数量
        status: 状态筛选

    Returns:
        {"success": bool, "records": list, "total": int, "page": int, "page_size": int}
    """
    import requests

    offset = (page - 1) * page_size

    # 构建查询 URL
    url = f"{SUPABASE_URL}/rest/v1/history_records?select=*"

    if status:
        url += f"&status=eq.{status}"

    url += f"&order=created_at.desc&offset={offset}&limit={page_size}"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Prefer": "count=exact"  # 获取总数
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        records = response.json()

        # 从 Content-Range 头获取总数
        content_range = response.headers.get("Content-Range", "")
        total = 0
        if "/" in content_range:
            total_str = content_range.split("/")[-1]
            if total_str != "*":
                total = int(total_str)

        return {
            "success": True,
            "records": records,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    except Exception as e:
        logger.error(f"获取历史记录列表失败: {e}")
        return {"success": False, "error": str(e), "records": [], "total": 0}


def search_history_records(keyword: str, limit: int = 20) -> Dict[str, Any]:
    """
    搜索历史记录

    Args:
        keyword: 搜索关键词
        limit: 返回数量限制

    Returns:
        {"success": bool, "records": list}
    """
    import requests

    # 使用 ilike 进行模糊搜索
    url = f"{SUPABASE_URL}/rest/v1/history_records?select=*&title=ilike.*{keyword}*&order=created_at.desc&limit={limit}"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        records = response.json()
        return {"success": True, "records": records}
    except Exception as e:
        logger.error(f"搜索历史记录失败: {e}")
        return {"success": False, "error": str(e), "records": []}


def get_history_statistics() -> Dict[str, Any]:
    """
    获取历史记录统计信息

    Returns:
        {"success": bool, "statistics": dict}
    """
    import requests

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    try:
        # 获取总数
        total_url = f"{SUPABASE_URL}/rest/v1/history_records?select=id"
        response = requests.get(total_url, headers={**headers, "Prefer": "count=exact"})
        content_range = response.headers.get("Content-Range", "0-0/0")
        total = int(content_range.split("/")[-1]) if "/" in content_range else 0

        # 获取各状态数量
        stats = {"total": total, "by_status": {}}

        for status in ["draft", "generating", "partial", "completed", "error"]:
            status_url = f"{SUPABASE_URL}/rest/v1/history_records?select=id&status=eq.{status}"
            response = requests.get(status_url, headers={**headers, "Prefer": "count=exact"})
            content_range = response.headers.get("Content-Range", "0-0/0")
            count = int(content_range.split("/")[-1]) if "/" in content_range else 0
            stats["by_status"][status] = count

        return {"success": True, "statistics": stats}
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return {"success": False, "error": str(e)}
