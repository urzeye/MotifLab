"""
Playwright-based 小红书发布服务

使用 Playwright 直接控制浏览器，绕过 VibeSurf 的 DOM 提取限制。
复用 VibeSurf 的浏览器配置文件以保持登录状态。
"""

import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)


class PlaywrightPublisher:
    """
    使用 Playwright 发布到小红书

    特点：
    - 直接控制 Chromium 浏览器
    - 复用 VibeSurf 的用户数据目录（保持登录状态）
    - 更可靠的元素定位和交互
    """

    # 浏览器配置 - 使用独立的 RenderInk 配置文件
    CHROMIUM_PATH = "/Users/joshuaspc/Library/Caches/ms-playwright/chromium-1194/chrome-mac/Chromium.app/Contents/MacOS/Chromium"
    USER_DATA_DIR = "/Users/joshuaspc/Library/Application Support/RenderInk/browser_profile"

    # 小红书 URL
    PUBLISH_URL = "https://creator.xiaohongshu.com/publish/publish"

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def start(self) -> bool:
        """启动浏览器"""
        try:
            logger.info("启动 Playwright 浏览器...")

            self.playwright = await async_playwright().start()

            # 使用持久化上下文来复用 VibeSurf 的登录状态
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.USER_DATA_DIR,
                executable_path=self.CHROMIUM_PATH,
                headless=False,  # 显示浏览器窗口
                viewport={"width": 1280, "height": 900},
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run",
                    "--disable-default-apps",
                ]
            )

            # 获取或创建页面
            if self.context.pages:
                self.page = self.context.pages[0]
            else:
                self.page = await self.context.new_page()

            logger.info("Playwright 浏览器启动成功")
            return True

        except Exception as e:
            logger.error(f"启动浏览器失败: {e}")
            return False

    async def stop(self):
        """关闭浏览器"""
        try:
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Playwright 浏览器已关闭")
        except Exception as e:
            logger.error(f"关闭浏览器失败: {e}")

    async def check_login(self) -> Dict[str, Any]:
        """检查登录状态"""
        try:
            await self.page.goto(self.PUBLISH_URL, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)

            current_url = self.page.url

            if "login" in current_url.lower():
                return {
                    "logged_in": False,
                    "message": "需要登录小红书",
                    "url": current_url
                }

            # 检查是否有发布页面的元素
            try:
                await self.page.wait_for_selector("text=上传图文", timeout=10000)
                return {
                    "logged_in": True,
                    "message": "已登录小红书",
                    "url": current_url
                }
            except:
                return {
                    "logged_in": False,
                    "message": "页面加载异常",
                    "url": current_url
                }

        except Exception as e:
            logger.error(f"检查登录状态失败: {e}")
            return {
                "logged_in": False,
                "message": f"检查失败: {str(e)}",
                "url": ""
            }

    async def publish(
        self,
        images: List[str],
        title: str,
        content: str,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        发布图文到小红书

        Args:
            images: 图片文件路径列表
            title: 标题（最多20字）
            content: 正文内容
            tags: 标签列表

        Returns:
            dict: 发布结果
        """
        try:
            logger.info(f"开始发布: title={title[:20]}, images={len(images)}")

            # 1. 导航到发布页面
            logger.info("步骤1: 导航到发布页面")
            await self.page.goto(self.PUBLISH_URL, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(5)  # 等待 Vue 渲染

            # 检查是否需要登录
            if "login" in self.page.url.lower():
                return {
                    "success": False,
                    "error": "需要登录小红书",
                    "step": "login_check"
                }

            # 2. 点击"上传图文"切换到图文模式
            logger.info("步骤2: 切换到图文上传模式")
            try:
                upload_text_btn = await self.page.wait_for_selector("text=上传图文", timeout=10000)
                await upload_text_btn.click()
                await asyncio.sleep(2)
                logger.info("已切换到图文模式")
            except Exception as e:
                logger.warning(f"切换图文模式失败，可能已在该模式: {e}")

            # 3. 上传图片
            logger.info(f"步骤3: 上传 {len(images)} 张图片")

            # 验证图片文件
            valid_images = [img for img in images if os.path.exists(img)]
            if not valid_images:
                return {
                    "success": False,
                    "error": "没有有效的图片文件",
                    "step": "validate_images"
                }

            # 找到文件上传 input
            try:
                # 小红书图文上传通常有一个隐藏的 file input
                file_input = await self.page.wait_for_selector(
                    'input[type="file"][accept*="image"]',
                    timeout=10000,
                    state="attached"
                )

                # 上传所有图片
                await file_input.set_input_files(valid_images)
                logger.info(f"已选择 {len(valid_images)} 张图片")

                # 等待图片上传完成
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"上传图片失败: {e}")
                # 尝试点击上传区域
                try:
                    upload_area = await self.page.wait_for_selector(
                        "text=拖拽图片", timeout=5000
                    )
                    await upload_area.click()
                    await asyncio.sleep(1)

                    # 再次尝试找到 file input
                    file_input = await self.page.wait_for_selector(
                        'input[type="file"]',
                        timeout=5000,
                        state="attached"
                    )
                    await file_input.set_input_files(valid_images)
                    await asyncio.sleep(5)
                except Exception as e2:
                    return {
                        "success": False,
                        "error": f"上传图片失败: {str(e2)}",
                        "step": "upload_images"
                    }

            # 4. 填写标题
            logger.info("步骤4: 填写标题")
            safe_title = title[:20] if len(title) > 20 else title

            try:
                # 查找标题输入框
                title_input = await self.page.wait_for_selector(
                    'input[placeholder*="标题"], [placeholder*="标题"], [data-placeholder*="标题"]',
                    timeout=10000
                )
                await title_input.click()
                await title_input.fill(safe_title)
                logger.info(f"标题已填写: {safe_title}")
            except Exception as e:
                logger.warning(f"通过 placeholder 查找标题失败，尝试其他方式: {e}")
                try:
                    # 尝试通过文本查找
                    title_area = await self.page.wait_for_selector("text=填写标题", timeout=5000)
                    await title_area.click()
                    await self.page.keyboard.type(safe_title)
                except Exception as e2:
                    logger.error(f"填写标题失败: {e2}")

            await asyncio.sleep(1)

            # 5. 填写正文
            logger.info("步骤5: 填写正文")
            try:
                # 查找正文输入区域
                content_input = await self.page.wait_for_selector(
                    '[placeholder*="正文"], [data-placeholder*="正文"], [contenteditable="true"]',
                    timeout=10000
                )
                await content_input.click()
                await content_input.fill(content)
                logger.info("正文已填写")
            except Exception as e:
                logger.warning(f"通过 placeholder 查找正文失败，尝试其他方式: {e}")
                try:
                    content_area = await self.page.wait_for_selector("text=填写正文", timeout=5000)
                    await content_area.click()
                    await self.page.keyboard.type(content)
                except Exception as e2:
                    logger.error(f"填写正文失败: {e2}")

            await asyncio.sleep(1)

            # 6. 添加标签（可选）
            if tags and len(tags) > 0:
                logger.info(f"步骤6: 添加 {len(tags)} 个标签")
                try:
                    # 查找添加话题的按钮/区域
                    tag_btn = await self.page.wait_for_selector(
                        "text=添加话题, text=#, [placeholder*='话题']",
                        timeout=5000
                    )
                    await tag_btn.click()
                    await asyncio.sleep(1)

                    for tag in tags[:5]:  # 最多5个标签
                        await self.page.keyboard.type(f"#{tag}")
                        await self.page.keyboard.press("Enter")
                        await asyncio.sleep(0.5)

                    logger.info("标签已添加")
                except Exception as e:
                    logger.warning(f"添加标签失败: {e}")

            # 7. 点击发布
            logger.info("步骤7: 点击发布按钮")
            try:
                # 查找发布按钮
                publish_btn = await self.page.wait_for_selector(
                    'button:has-text("发布"), [class*="publish"]:has-text("发布")',
                    timeout=10000
                )
                await publish_btn.click()
                logger.info("已点击发布按钮")

                # 等待发布完成
                await asyncio.sleep(5)

                # 检查是否有确认弹窗
                try:
                    confirm_btn = await self.page.wait_for_selector(
                        "text=确认, text=确定",
                        timeout=3000
                    )
                    await confirm_btn.click()
                    await asyncio.sleep(3)
                except:
                    pass  # 没有确认弹窗

            except Exception as e:
                logger.error(f"点击发布失败: {e}")
                return {
                    "success": False,
                    "error": f"点击发布失败: {str(e)}",
                    "step": "publish"
                }

            # 8. 检查发布结果
            final_url = self.page.url

            # 如果不在发布页面了，说明可能成功了
            if "publish" not in final_url.lower() or "success" in final_url.lower():
                logger.info("发布成功！")
                return {
                    "success": True,
                    "message": "发布成功",
                    "url": final_url
                }
            else:
                return {
                    "success": True,
                    "message": "发布操作已执行，请检查浏览器确认结果",
                    "url": final_url
                }

        except Exception as e:
            logger.error(f"发布过程出错: {e}")
            return {
                "success": False,
                "error": str(e),
                "step": "unknown"
            }


async def test_playwright_publish():
    """测试 Playwright 发布功能"""
    publisher = PlaywrightPublisher()

    try:
        # 启动浏览器
        if not await publisher.start():
            print("启动浏览器失败")
            return

        # 检查登录状态
        login_status = await publisher.check_login()
        print(f"登录状态: {login_status}")

        if not login_status.get("logged_in"):
            print("请在浏览器中手动登录...")
            input("登录完成后按 Enter 继续...")

            # 再次检查
            login_status = await publisher.check_login()
            if not login_status.get("logged_in"):
                print("仍未登录，退出")
                return

        # 测试发布
        result = await publisher.publish(
            images=["/tmp/test_coffee.png"],
            title="Playwright测试发布",
            content="这是使用 Playwright 自动发布的测试内容，请忽略。",
            tags=["测试"]
        )

        print(f"发布结果: {result}")

    finally:
        await publisher.stop()


if __name__ == "__main__":
    asyncio.run(test_playwright_publish())
