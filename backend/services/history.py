import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path


class HistoryService:
    def __init__(self):
        self.history_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "history"
        )
        os.makedirs(self.history_dir, exist_ok=True)

        self.index_file = os.path.join(self.history_dir, "index.json")
        self._init_index()

    def _init_index(self):
        if not os.path.exists(self.index_file):
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump({"records": []}, f, ensure_ascii=False, indent=2)

    def _load_index(self) -> Dict:
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"records": []}

    def _save_index(self, index: Dict):
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def _get_record_path(self, record_id: str) -> str:
        return os.path.join(self.history_dir, f"{record_id}.json")

    def create_record(
        self,
        topic: str,
        outline: Dict,
        task_id: Optional[str] = None
    ) -> str:
        record_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        record = {
            "id": record_id,
            "title": topic,
            "created_at": now,
            "updated_at": now,
            "outline": outline,
            "images": {
                "task_id": task_id,
                "generated": []
            },
            "status": "draft",  # draft/generating/completed/partial
            "thumbnail": None
        }

        record_path = self._get_record_path(record_id)
        with open(record_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        index = self._load_index()
        index["records"].insert(0, {
            "id": record_id,
            "title": topic,
            "created_at": now,
            "updated_at": now,
            "status": "draft",
            "thumbnail": None,
            "page_count": len(outline.get("pages", []))
        })
        self._save_index(index)

        return record_id

    def get_record(self, record_id: str) -> Optional[Dict]:
        record_path = self._get_record_path(record_id)

        if not os.path.exists(record_path):
            return None

        try:
            with open(record_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def update_record(
        self,
        record_id: str,
        outline: Optional[Dict] = None,
        images: Optional[Dict] = None,
        status: Optional[str] = None,
        thumbnail: Optional[str] = None
    ) -> bool:
        record = self.get_record(record_id)
        if not record:
            return False

        now = datetime.now().isoformat()
        record["updated_at"] = now

        if outline is not None:
            record["outline"] = outline

        if images is not None:
            record["images"] = images

        if status is not None:
            record["status"] = status

        if thumbnail is not None:
            record["thumbnail"] = thumbnail

        record_path = self._get_record_path(record_id)
        with open(record_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        index = self._load_index()
        for idx_record in index["records"]:
            if idx_record["id"] == record_id:
                idx_record["updated_at"] = now
                if status:
                    idx_record["status"] = status
                if thumbnail:
                    idx_record["thumbnail"] = thumbnail
                if outline:
                    idx_record["page_count"] = len(outline.get("pages", []))
                break

        self._save_index(index)
        return True

    def delete_record(self, record_id: str) -> bool:
        record = self.get_record(record_id)
        if not record:
            return False

        if record.get("images") and record["images"].get("generated"):
            output_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "output"
            )
            for img_file in record["images"]["generated"]:
                img_path = os.path.join(output_dir, img_file)
                if os.path.exists(img_path):
                    try:
                        os.remove(img_path)
                    except Exception as e:
                        print(f"删除图片失败: {img_file}, {e}")

        record_path = self._get_record_path(record_id)
        try:
            os.remove(record_path)
        except Exception:
            return False

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
        index = self._load_index()
        records = index.get("records", [])

        if status:
            records = [r for r in records if r.get("status") == status]

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
        index = self._load_index()
        records = index.get("records", [])

        keyword_lower = keyword.lower()
        results = [
            r for r in records
            if keyword_lower in r.get("title", "").lower()
        ]

        return results

    def get_statistics(self) -> Dict:
        index = self._load_index()
        records = index.get("records", [])

        total = len(records)
        status_count = {}

        for record in records:
            status = record.get("status", "draft")
            status_count[status] = status_count.get(status, 0) + 1

        return {
            "total": total,
            "by_status": status_count
        }


_service_instance = None


def get_history_service() -> HistoryService:
    global _service_instance
    if _service_instance is None:
        _service_instance = HistoryService()
    return _service_instance
