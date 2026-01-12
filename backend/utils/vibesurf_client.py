"""
VibeSurf 浏览器自动化客户端

VibeSurf 是一个浏览器自动化服务，运行在本地 http://127.0.0.1:9335
提供浏览器操作、AI 自动化代理和平台 API 调用等功能。
"""

import logging
import requests
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class VibeSurfError(Exception):
    """VibeSurf 相关错误"""
    pass


class VibeSurfClient:
    """
    VibeSurf 浏览器自动化客户端

    提供以下核心功能：
    - 健康检查：检查 VibeSurf 服务状态
    - 浏览器状态：获取当前浏览器状态（标签页、DOM 等）
    - 浏览器操作：执行导航、点击、输入等操作
    - AI 代理：执行复杂的多步骤自动化任务
    - 平台 API：调用小红书等平台的 API
    """

    BASE_URL = "http://127.0.0.1:9335"
    TIMEOUT = 30  # 默认超时时间（秒）
    AGENT_TIMEOUT = 120  # AI 代理任务超时时间（秒）

    def __init__(self, base_url: str = None, timeout: int = None):
        """
        初始化 VibeSurf 客户端

        Args:
            base_url: VibeSurf 服务地址，默认为 http://127.0.0.1:9335
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout or self.TIMEOUT
        logger.debug(f"VibeSurfClient 初始化: base_url={self.base_url}")

    def check_health(self) -> Dict[str, Any]:
        """
        检查 VibeSurf 运行状态

        Returns:
            dict: 包含状态信息
                - running: bool, 服务是否运行中
                - message: str, 状态消息
                - version: str, 版本信息（如果有）
        """
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=5  # 健康检查使用较短的超时
            )

            if response.status_code == 200:
                data = response.json() if response.text else {}
                return {
                    "running": True,
                    "message": "VibeSurf 服务运行正常",
                    "version": data.get("version", "unknown"),
                    "data": data
                }
            else:
                return {
                    "running": False,
                    "message": f"VibeSurf 服务异常，状态码: {response.status_code}",
                    "version": None
                }

        except requests.exceptions.ConnectionError:
            logger.warning("无法连接到 VibeSurf 服务")
            return {
                "running": False,
                "message": "无法连接到 VibeSurf 服务，请确保 VibeSurf 已启动 (vibesurf 命令)",
                "version": None
            }
        except requests.exceptions.Timeout:
            logger.warning("连接 VibeSurf 服务超时")
            return {
                "running": False,
                "message": "连接 VibeSurf 服务超时",
                "version": None
            }
        except Exception as e:
            logger.error(f"检查 VibeSurf 状态失败: {e}")
            return {
                "running": False,
                "message": f"检查 VibeSurf 状态失败: {str(e)}",
                "version": None
            }

    def list_actions(self, keyword: str = None) -> Dict[str, Any]:
        """
        列出可用的浏览器操作

        Args:
            keyword: 可选的搜索关键词

        Returns:
            dict: 可用操作列表
        """
        try:
            params = {}
            if keyword:
                params["keyword"] = keyword

            response = requests.get(
                f"{self.base_url}/api/tool/search",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            return {
                "success": True,
                "actions": response.json()
            }

        except Exception as e:
            logger.error(f"获取操作列表失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "actions": []
            }

    def get_action_params(self, action_name: str) -> Dict[str, Any]:
        """
        获取指定操作的参数定义

        Args:
            action_name: 操作名称，如 browser.navigate, browser.click

        Returns:
            dict: 参数 JSON Schema
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tool/{action_name}/params",
                timeout=self.timeout
            )
            response.raise_for_status()
            return {
                "success": True,
                "params": response.json()
            }

        except Exception as e:
            logger.error(f"获取操作参数失败 [{action_name}]: {e}")
            return {
                "success": False,
                "error": str(e),
                "params": {}
            }

    def get_browser_state(self) -> Dict[str, Any]:
        """
        获取浏览器当前状态

        返回当前打开的标签页列表、当前活动标签、DOM 内容等信息。
        这是进行浏览器操作前的重要步骤。

        Returns:
            dict: 浏览器状态信息
                - success: bool
                - tabs: list, 标签页列表
                - current_tab: str, 当前标签页 ID
                - page_content: str, 页面内容
        """
        return self.execute_action("get_browser_state", {})

    def execute_action(self, action_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行浏览器操作

        常用操作：
        - browser.navigate: 导航到 URL，参数 {"url": "https://..."}
        - browser.click: 点击元素，参数 {"index": 1} 或 {"selector": "..."}
        - browser.input: 输入文本，参数 {"index": 1, "text": "..."}
        - browser.scroll: 滚动页面，参数 {"direction": "down", "amount": 500}
        - browser.wait: 等待，参数 {"seconds": 2}
        - browser.switch: 切换标签页，参数 {"tab_id": "..."}
        - browser.send_keys: 发送按键，参数 {"keys": "Enter"}

        Args:
            action_name: 操作名称
            parameters: 操作参数

        Returns:
            dict: 操作结果
                - success: bool
                - result: any, 操作返回值
                - error: str, 错误信息（如果失败）
        """
        try:
            logger.debug(f"执行浏览器操作: {action_name}, 参数: {parameters}")

            response = requests.post(
                f"{self.base_url}/api/tool/execute",
                json={
                    "action_name": action_name,
                    "parameters": parameters
                },
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()
            logger.debug(f"操作完成: {action_name}, success={result.get('success', True)}")

            return {
                "success": result.get("success", True),
                "result": result.get("result"),
                "extracted_content": result.get("extracted_content"),
                "attachments": result.get("attachments", []),
                "raw_response": result
            }

        except requests.exceptions.Timeout:
            logger.error(f"执行操作超时: {action_name}")
            return {
                "success": False,
                "error": f"操作超时: {action_name}",
                "result": None
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"执行操作失败 [{action_name}]: {e}")
            return {
                "success": False,
                "error": str(e),
                "result": None
            }
        except Exception as e:
            logger.error(f"执行操作异常 [{action_name}]: {e}")
            return {
                "success": False,
                "error": str(e),
                "result": None
            }

    def execute_agent(self, task: str, tab_id: str = None, task_files: List[str] = None, timeout: int = None) -> Dict[str, Any]:
        """
        执行 AI 自动化代理 (browser-use)

        启动一个 AI 子代理来完成复杂的多步骤浏览器任务。
        适用于：
        - 复杂的表单填写
        - 多步骤工作流
        - 需要动态判断的任务
        - 文件上传

        Args:
            task: 任务描述，应该描述目标而非具体步骤
                  好的例子: "在小红书发布一篇图文，标题为xxx，内容为xxx"
                  差的例子: "点击发布按钮，然后输入标题..."
            tab_id: 可选的标签页 ID，不指定则创建新标签页
            task_files: 可选的文件路径列表，用于上传文件
            timeout: 超时时间（秒），默认 120 秒

        Returns:
            dict: 执行结果
                - success: bool
                - result: any, 任务结果
                - error: str, 错误信息（如果失败）
        """
        try:
            logger.info(f"启动 AI 代理任务: {task[:100]}...")

            # VibeSurf 需要 tasks 数组格式
            task_obj = {"task": task}
            if tab_id:
                task_obj["tab_id"] = tab_id
            if task_files:
                task_obj["task_files"] = task_files

            parameters = {"tasks": [task_obj]}

            response = requests.post(
                f"{self.base_url}/api/tool/execute",
                json={
                    "action_name": "execute_browser_use_agent",
                    "parameters": parameters
                },
                timeout=timeout or self.AGENT_TIMEOUT
            )
            response.raise_for_status()

            result = response.json()
            success = result.get("success", True)

            if success:
                logger.info("AI 代理任务完成")
            else:
                logger.warning(f"AI 代理任务失败: {result.get('result', 'unknown error')}")

            return {
                "success": success,
                "result": result.get("result"),
                "extracted_content": result.get("extracted_content"),
                "raw_response": result
            }

        except requests.exceptions.Timeout:
            logger.error("AI 代理任务超时")
            return {
                "success": False,
                "error": f"AI 代理任务超时（{timeout or self.AGENT_TIMEOUT}秒）",
                "result": None
            }
        except Exception as e:
            logger.error(f"AI 代理任务失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "result": None
            }

    def call_website_api(self, platform: str, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        调用小红书等平台 API

        支持的平台：
        - xiaohongshu (小红书)
        - weibo (微博)
        - zhihu (知乎)
        - douyin (抖音)
        - youtube

        Args:
            platform: 平台名称
            method: API 方法名
            params: API 参数

        Returns:
            dict: API 返回结果
        """
        try:
            logger.debug(f"调用平台 API: {platform}.{method}")

            parameters = {
                "platform": platform,
                "method": method,
            }
            if params:
                parameters["params"] = params

            return self.execute_action("call_website_api", parameters)

        except Exception as e:
            logger.error(f"调用平台 API 失败 [{platform}.{method}]: {e}")
            return {
                "success": False,
                "error": str(e),
                "result": None
            }

    def get_website_api_params(self, platform: str) -> Dict[str, Any]:
        """
        获取平台 API 的可用方法和参数

        Args:
            platform: 平台名称，如 xiaohongshu, weibo, zhihu

        Returns:
            dict: 平台 API 定义
        """
        try:
            return self.execute_action("get_website_api_params", {"platform": platform})
        except Exception as e:
            logger.error(f"获取平台 API 参数失败 [{platform}]: {e}")
            return {
                "success": False,
                "error": str(e),
                "result": None
            }

    # ==================== 便捷方法 ====================

    def navigate(self, url: str) -> Dict[str, Any]:
        """导航到指定 URL"""
        return self.execute_action("browser.navigate", {"url": url})

    def click(self, index: int = None, selector: str = None) -> Dict[str, Any]:
        """
        点击元素

        Args:
            index: 元素索引（从 get_browser_state 获取）
            selector: CSS 选择器（可选）
        """
        params = {}
        if index is not None:
            params["index"] = index
        if selector:
            params["selector"] = selector
        return self.execute_action("browser.click", params)

    def input_text(self, text: str, index: int = None, selector: str = None, clear: bool = True) -> Dict[str, Any]:
        """
        输入文本

        Args:
            text: 要输入的文本
            index: 元素索引
            selector: CSS 选择器
            clear: 是否先清空输入框
        """
        params = {"text": text}
        if index is not None:
            params["index"] = index
        if selector:
            params["selector"] = selector
        if clear:
            params["clear"] = clear
        return self.execute_action("browser.input", params)

    def scroll(self, direction: str = "down", amount: int = 500) -> Dict[str, Any]:
        """
        滚动页面

        Args:
            direction: 滚动方向，up 或 down
            amount: 滚动像素数
        """
        return self.execute_action("browser.scroll", {
            "direction": direction,
            "amount": amount
        })

    def wait(self, seconds: float = 1) -> Dict[str, Any]:
        """等待指定秒数"""
        return self.execute_action("browser.wait", {"seconds": seconds})

    def send_keys(self, keys: str) -> Dict[str, Any]:
        """
        发送按键

        Args:
            keys: 按键名称，如 "Enter", "Tab", "Escape" 等
        """
        return self.execute_action("browser.send_keys", {"keys": keys})

    def evaluate_js(self, script: str) -> Dict[str, Any]:
        """
        执行 JavaScript 代码

        Args:
            script: JavaScript 代码
        """
        return self.execute_action("browser.evaluate", {"script": script})


# 全局客户端实例
_vibesurf_client: Optional[VibeSurfClient] = None


def get_vibesurf_client() -> VibeSurfClient:
    """获取全局 VibeSurf 客户端实例"""
    global _vibesurf_client
    if _vibesurf_client is None:
        _vibesurf_client = VibeSurfClient()
    return _vibesurf_client


def reset_vibesurf_client():
    """重置全局客户端实例"""
    global _vibesurf_client
    _vibesurf_client = None
