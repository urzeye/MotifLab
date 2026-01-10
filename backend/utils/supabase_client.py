"""
Supabase 客户端

用于与 Supabase 数据库交互，存储发布记录等数据。
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Supabase 配置
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://cnwgxcvsunbxclgkykln.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNud2d4Y3ZzdW5ieGNsZ2t5a2xuIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NzYwMTc1NCwiZXhwIjoyMDgzMTc3NzU0fQ.CVTRoi-M992K6DjAGW_MNQ83pzFxAE33jfgIkbLcLSU")

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
        result = client.table("xiaohongshu_posts").insert(data)
        logger.info(f"创建发布记录成功: {result.get('id', 'unknown')}")
        return {"success": True, "record": result}
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
        return {"success": True, "record": result.get("data", [])}
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
        return {"success": True, "records": result.get("data", [])}
    except Exception as e:
        logger.error(f"获取发布记录失败: {e}")
        return {"success": False, "error": str(e), "records": []}


def get_publish_record(record_id: str) -> Dict[str, Any]:
    """获取单条发布记录"""
    client = get_supabase_client()

    try:
        result = client.table("xiaohongshu_posts").select("*").eq("id", record_id).execute()
        records = result.get("data", [])
        if records:
            return {"success": True, "record": records[0]}
        return {"success": False, "error": "记录不存在"}
    except Exception as e:
        logger.error(f"获取发布记录失败: {e}")
        return {"success": False, "error": str(e)}
