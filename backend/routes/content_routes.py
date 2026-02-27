"""
内容生成相关 API 路由

包含功能：
- 生成标题、文案、标签
"""

import time
import logging
from flask import Blueprint, request
from backend.application.services import get_content_application_service
from backend.interfaces.http import json_response
from .utils import log_request, log_error

logger = logging.getLogger(__name__)
content_application_service = get_content_application_service()


def create_content_blueprint():
    """创建内容生成路由蓝图（工厂函数，支持多次调用）"""
    content_bp = Blueprint('content', __name__)

    @content_bp.route('/content', methods=['POST'])
    def generate_content():
        """
        生成标题、文案、标签

        请求格式（application/json）：
        - topic: 主题文本
        - outline: 大纲内容
        - record_id: 历史记录 ID（可选，传入后会自动回写 content）

        返回：
        - success: 是否成功
        - titles: 标题列表（3个备选）
        - copywriting: 文案正文
        - tags: 标签列表
        """
        start_time = time.time()

        try:
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                data = {}
            topic = data.get('topic', '')
            outline = data.get('outline', '')
            record_id = data.get('record_id')

            log_request('/content', {
                'topic': topic[:50] if topic else '',
                'outline_length': len(outline),
                'record_id': record_id
            })

            # 验证必填参数
            if not topic:
                logger.warning("内容生成请求缺少 topic 参数")
                return json_response({
                    "success": False,
                    "error": "参数错误：topic 不能为空。\n请提供主题内容。"
                }, 400)

            if not outline:
                logger.warning("内容生成请求缺少 outline 参数")
                return json_response({
                    "success": False,
                    "error": "参数错误：outline 不能为空。\n请先生成大纲。"
                }, 400)

            # 调用内容生成服务
            logger.info(f"🔄 开始生成内容，主题: {topic[:50]}...")
            result = content_application_service.generate_content(
                topic=topic,
                outline=outline,
                record_id=record_id,
            )

            # 记录结果
            elapsed = time.time() - start_time
            if result["success"]:
                logger.info(f"✅ 内容生成成功，耗时 {elapsed:.2f}s")
                return json_response(result, 200)
            else:
                logger.error(f"❌ 内容生成失败: {result.get('error', '未知错误')}")
                return json_response(result, 500)

        except Exception as e:
            log_error('/content', e)
            error_msg = str(e)
            return json_response({
                "success": False,
                "error": f"内容生成异常。\n错误详情: {error_msg}\n建议：检查后端日志获取更多信息"
            }, 500)

    return content_bp
