"""异步图片任务 API 路由。"""

from __future__ import annotations

import logging
from flask import Blueprint, request

from backend.application.services import get_image_job_application_service
from backend.interfaces.http import json_response

logger = logging.getLogger(__name__)
image_job_app_service = get_image_job_application_service()


def _is_valid_page(page: dict) -> bool:
    """校验页面结构。"""
    if not isinstance(page, dict):
        return False
    if "index" not in page or "type" not in page or "content" not in page:
        return False
    if not isinstance(page.get("index"), int):
        return False
    if not isinstance(page.get("type"), str):
        return False
    if not isinstance(page.get("content"), str):
        return False
    return True


def create_image_job_blueprint():
    """创建异步图片任务蓝图。"""
    bp = Blueprint("image_jobs", __name__)

    @bp.route("/image-jobs", methods=["POST"])
    def create_image_job():
        """
        创建异步图片任务

        请求体：
        - pages: 页面列表（必填）
        - task_id/full_outline/user_topic/user_images/user_prompt/system_prompt（可选）
        """
        try:
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                data = {}

            pages = data.get("pages")
            if not isinstance(pages, list) or not pages:
                return json_response({"success": False, "error": "参数错误：pages 不能为空"}, 400)
            if any(not _is_valid_page(page) for page in pages):
                return json_response({"success": False, "error": "参数错误：pages 格式不正确"}, 400)

            job_id = image_job_app_service.create_job(
                pages=pages,
                task_id=data.get("task_id"),
                full_outline=str(data.get("full_outline") or ""),
                user_images_base64=data.get("user_images") if isinstance(data.get("user_images"), list) else [],
                user_topic=str(data.get("user_topic") or ""),
                user_prompt=str(data.get("user_prompt", data.get("custom_prompt", "")) or "").strip(),
                system_prompt=str(data.get("system_prompt") or "").strip(),
            )
            return json_response({"success": True, "job_id": job_id, "status": "queued"}, 200)
        except Exception as exc:
            logger.exception(f"创建异步图片任务失败: {exc}")
            return json_response({"success": False, "error": str(exc)}, 500)

    @bp.route("/image-jobs/<job_id>", methods=["GET"])
    def get_image_job(job_id: str):
        """获取异步图片任务详情。"""
        try:
            result = image_job_app_service.get_job(job_id)
            if not result:
                return json_response({"success": False, "error": "任务不存在"}, 404)
            return json_response({"success": True, "data": result}, 200)
        except Exception as exc:
            logger.exception(f"获取异步图片任务失败: {exc}")
            return json_response({"success": False, "error": str(exc)}, 500)

    @bp.route("/image-jobs", methods=["GET"])
    def list_image_jobs():
        """分页查询异步图片任务。"""
        try:
            page = request.args.get("page", 1, type=int)
            page_size = request.args.get("page_size", 20, type=int)
            status = (request.args.get("status") or "").strip() or None
            result = image_job_app_service.list_jobs(page=page, page_size=page_size, status=status)
            return json_response({"success": True, **result}, 200)
        except Exception as exc:
            logger.exception(f"查询异步图片任务失败: {exc}")
            return json_response({"success": False, "error": str(exc)}, 500)

    @bp.route("/image-jobs/<job_id>/cancel", methods=["POST"])
    def cancel_image_job(job_id: str):
        """请求取消异步图片任务。"""
        try:
            success = image_job_app_service.cancel_job(job_id)
            if not success:
                return json_response({"success": False, "error": "任务不存在或不可取消"}, 404)
            return json_response({"success": True, "job_id": job_id, "cancel_requested": True}, 200)
        except Exception as exc:
            logger.exception(f"取消异步图片任务失败: {exc}")
            return json_response({"success": False, "error": str(exc)}, 500)

    return bp
