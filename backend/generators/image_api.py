"""Image API 图片生成器"""
import logging
import base64
import os
import requests
from typing import Dict, Any, Optional, List, Union
from .base import ImageGeneratorBase
from ..utils.image_compressor import compress_image

logger = logging.getLogger(__name__)


def _get_timeout(env_key: str, default: int) -> int:
    """读取整型超时配置，非法值回退默认值"""
    try:
        value = int(os.getenv(env_key, str(default)))
        return value if value > 0 else default
    except Exception:
        return default


IMAGE_API_TIMEOUT = _get_timeout("IMAGE_API_TIMEOUT", 300)
IMAGE_DOWNLOAD_TIMEOUT = _get_timeout("IMAGE_DOWNLOAD_TIMEOUT", 60)


class ImageApiGenerator(ImageGeneratorBase):
    """Image API 生成器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        logger.debug("初始化 ImageApiGenerator...")
        self.base_url = config.get('base_url', 'https://api.example.com').rstrip('/').rstrip('/v1')
        self.model = config.get('model', 'default-model')
        self.text_model = config.get('text_model')
        self.edit_model = config.get('edit_model')
        self.default_aspect_ratio = config.get('default_aspect_ratio', '3:4')
        self.image_size = config.get('image_size', '4K')
        # 默认保持历史行为：直接发送尺寸标签（如 4K）。
        # 关闭后将常见标签转换为标准分辨率字符串。
        self.use_size_tag = config.get('use_size_tag', True)
        # 添加对 SiliconFlow API 的 size 参数支持
        self.size = config.get('size', '1024x1024')  # SiliconFlow API 需要的尺寸格式

        # 支持自定义端点路径
        endpoint_type = config.get('endpoint_type', '/v1/images/generations')
        # 兼容旧的简写格式
        if endpoint_type == 'images':
            endpoint_type = '/v1/images/generations'
        elif endpoint_type == 'chat':
            endpoint_type = '/v1/chat/completions'
        # 确保以 / 开头
        if not endpoint_type.startswith('/'):
            endpoint_type = '/' + endpoint_type
        self.endpoint_type = endpoint_type

        logger.info(f"ImageApiGenerator 初始化完成: base_url={self.base_url}, model={self.model}, endpoint={self.endpoint_type}")

    def validate_config(self) -> bool:
        """验证配置是否有效"""
        if not self.api_key:
            logger.error("Image API Key 未配置")
            raise ValueError(
                "Image API Key 未配置。\n"
                "解决方案：在系统设置页面编辑该服务商，填写 API Key"
            )
        return True

    def get_supported_sizes(self) -> List[str]:
        """获取支持的图片尺寸"""
        return ["1K", "2K", "4K"]

    def get_supported_aspect_ratios(self) -> List[str]:
        """获取支持的宽高比"""
        return ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]

    def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = None,
        temperature: float = 1.0,
        model: str = None,
        reference_image: Optional[bytes] = None,
        reference_images: Optional[List[bytes]] = None,
        **kwargs
    ) -> bytes:
        """
        生成图片

        Args:
            prompt: 图片描述
            aspect_ratio: 宽高比
            temperature: 创意度（未使用，保留接口兼容）
            model: 模型名称
            reference_image: 单张参考图片数据（向后兼容）
            reference_images: 多张参考图片数据列表

        Returns:
            生成的图片二进制数据
        """
        self.validate_config()

        if aspect_ratio is None:
            aspect_ratio = self.default_aspect_ratio

        if model is None:
            model = self.model

        logger.info(f"Image API 生成图片: model={model}, aspect_ratio={aspect_ratio}, endpoint={self.endpoint_type}")

        # 根据端点类型选择不同的生成方式
        if 'chat' in self.endpoint_type or 'completions' in self.endpoint_type:
            return self._generate_via_chat_api(prompt, aspect_ratio, model, reference_image, reference_images)
        else:
            return self._generate_via_images_api(prompt, aspect_ratio, model, reference_image, reference_images)

    def _generate_via_images_api(
        self,
        prompt: str,
        aspect_ratio: str,
        model: str,
        reference_image: Optional[bytes] = None,
        reference_images: Optional[List[bytes]] = None
    ) -> bytes:
        """通过 /v1/images/generations 端点生成图片"""
        base_url_lower = (self.base_url or "").lower()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # SiliconFlow: 部分场景需要使用不同的模型名（文生图 vs 图像编辑）。
        # 若传入的 model 不是 SiliconFlow 官方模型ID，会触发 code=20012 (Model does not exist)
        # 这里仅对 siliconflow.cn 做兼容，不影响其他服务商。
        selected_model = model
        if 'siliconflow.cn' in base_url_lower:
            model_lower = (model or "").lower()
            alias_map = {
                'qwen-image-max': 'Qwen/Qwen-Image-Edit',
                'qwen-image-edit': 'Qwen/Qwen-Image-Edit',
                'qwen-image': 'Qwen/Qwen-Image',
            }
            if model_lower in alias_map:
                selected_model = alias_map[model_lower]

        if self.use_size_tag:
            final_image_size = self.image_size
        else:
            # 常见标签回退到标准分辨率，兼容严格校验 size 的 OpenAI 兼容接口
            size_mapping = {
                "1K": "1024x1024",
                "2K": "1024x1024",
                "4K": "1024x1024",
                "HD": "1024x1024",
            }
            final_image_size = size_mapping.get(self.image_size, self.image_size)

        payload = {
            "model": selected_model,
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "image_size": final_image_size,
            "size": self.size  # SiliconFlow API 需要的 size 参数
        }

        # 收集所有参考图片
        all_reference_images = []
        if reference_images and len(reference_images) > 0:
            all_reference_images.extend(reference_images)
        if reference_image and reference_image not in all_reference_images:
            all_reference_images.append(reference_image)

        # 检查是否是需要参考图片的模型（如 Qwen-Image-Edit 系列）
        edit_models = [
            'qwen-image-edit',
            'Qwen/Qwen-Image-Edit',
            'Qwen/Qwen-Image-Edit-2509',
            'qwen-image-max'  # 根据错误信息，这个模型也需要图片
        ]

        # SiliconFlow：带参考图时优先使用编辑模型；无参考图时优先使用文生图模型
        # 允许通过 config.edit_model / config.text_model 覆盖
        if 'siliconflow.cn' in base_url_lower:
            if all_reference_images:
                payload["model"] = self.edit_model or 'Qwen/Qwen-Image-Edit'
            else:
                payload["model"] = self.text_model or 'Qwen/Qwen-Image'

        model_lower = (payload.get("model") or "").lower()
        is_edit_model = any((edit_model or "").lower() in model_lower for edit_model in edit_models)

        # 如果是编辑模型但没有提供参考图片，抛出错误
        if is_edit_model and not all_reference_images:
            logger.error(f"模型 {model} 需要参考图片，但未提供")
            raise Exception(
                f"❌ 模型 {model} 需要参考图片才能生成\n\n"
                "【解决方案】\n"
                "1. 上传一张参考图片\n"
                "2. 或更换为不支持图片编辑的模型（如 Qwen-Image）\n\n"
                "【说明】\n"
                "Qwen-Image-Edit 系列模型需要参考图片来生成新图片"
            )

        # 如果有参考图片，添加到 image 数组
        if all_reference_images:
            logger.debug(f"  添加 {len(all_reference_images)} 张参考图片")
            image_uris = []
            for idx, img_data in enumerate(all_reference_images):
                compressed_img = compress_image(img_data, max_size_kb=200)
                logger.debug(f"  参考图 {idx}: {len(img_data)} -> {len(compressed_img)} bytes")
                base64_image = base64.b64encode(compressed_img).decode('utf-8')
                data_uri = f"data:image/png;base64,{base64_image}"
                image_uris.append(data_uri)

            if 'siliconflow.cn' in base_url_lower:
                payload["image"] = image_uris[0]
            else:
                payload["image"] = image_uris

            ref_count = len(all_reference_images)
            enhanced_prompt = f"""参考提供的 {ref_count} 张图片的风格（色彩、光影、构图、氛围），生成一张新图片。

新图片内容：{prompt}

要求：
1. 保持相似的色调和氛围
2. 使用相似的光影处理
3. 保持一致的画面质感
4. 如果参考图中有人物或产品，可以适当融入"""
            payload["prompt"] = enhanced_prompt

        api_url = f"{self.base_url}{self.endpoint_type}"
        logger.debug(f"  发送请求到: {api_url}")
        def _post_once() -> requests.Response:
            return requests.post(api_url, headers=headers, json=payload, timeout=IMAGE_API_TIMEOUT)

        response = _post_once()

        # SiliconFlow: 如果模型不存在（code=20012），自动回退到常见可用模型ID
        if response.status_code != 200 and 'siliconflow.cn' in base_url_lower:
            try:
                err_json = response.json()
            except Exception:
                err_json = None

            err_code = err_json.get('code') if isinstance(err_json, dict) else None
            if err_code == 20012:
                if all_reference_images:
                    candidates = [
                        self.edit_model,
                        'Qwen/Qwen-Image-Edit-2509',
                        'Qwen/Qwen-Image-Edit',
                    ]
                else:
                    candidates = [
                        self.text_model,
                        'Qwen/Qwen-Image',
                    ]

                seen = set()
                current = payload.get('model')
                for m in candidates:
                    if not m or m == current or m in seen:
                        continue
                    seen.add(m)
                    payload['model'] = m
                    logger.warning(f"SiliconFlow 模型不存在，自动重试 model={m}")
                    response = _post_once()
                    if response.status_code == 200:
                        break

        if response.status_code != 200:
            error_detail = response.text[:500]
            logger.error(f"Image API 请求失败: status={response.status_code}, error={error_detail}")
            raise Exception(
                f"Image API 请求失败 (状态码: {response.status_code})\n"
                f"错误详情: {error_detail}\n"
                f"请求地址: {api_url}\n"
                f"请求模型: {payload.get('model')}\n"
                "可能原因：\n"
                "1. API密钥无效或已过期\n"
                "2. 请求参数不符合API要求\n"
                "3. API服务端错误\n"
                "4. Base URL配置错误\n"
                "建议：检查API密钥和base_url配置"
            )

        result = response.json()
        logger.debug(f"  API 响应: {str(result)[:200]}")

        # SiliconFlow API 返回格式: {'images': [{'url': '...'}], 'data': [{'url': '...'}]}
        # 检查 images 字段
        if "images" in result and len(result["images"]) > 0:
            image_url = result["images"][0].get("url")
            if image_url:
                logger.info(f"✅ 获取到图片 URL，开始下载...")
                return self._download_image(image_url)

        # 检查 data 字段（兼容其他 API）
        if "data" in result and len(result["data"]) > 0:
            item = result["data"][0]

            # 检查 URL 格式
            if "url" in item:
                logger.info(f"✅ 获取到图片 URL，开始下载...")
                return self._download_image(item["url"])

            # 检查 base64 格式
            if "b64_json" in item:
                b64_data_uri = item["b64_json"]
                if b64_data_uri.startswith('data:'):
                    b64_string = b64_data_uri.split(',', 1)[1]
                else:
                    b64_string = b64_data_uri
                image_data = base64.b64decode(b64_string)
                logger.info(f"✅ Image API 图片生成成功: {len(image_data)} bytes")
                return image_data

        logger.error(f"无法从响应中提取图片数据: {str(result)[:200]}")
        raise Exception(
            f"图片数据提取失败：未找到有效的图片数据。\n"
            f"API响应片段: {str(result)[:500]}\n"
            "可能原因：\n"
            "1. API返回格式与预期不符\n"
            "2. 该模型不支持 base64 格式，只支持 URL\n"
            "3. response_format 参数未生效\n"
            "建议：检查API文档确认返回格式要求"
        )

    def _generate_via_chat_api(
        self,
        prompt: str,
        aspect_ratio: str,
        model: str,
        reference_image: Optional[bytes] = None,
        reference_images: Optional[List[bytes]] = None
    ) -> bytes:
        """通过 /v1/chat/completions 端点生成图片（如即梦 API）"""
        import re

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 构建用户消息内容
        user_content: Any = prompt

        # 收集所有参考图片
        all_reference_images = []
        if reference_images and len(reference_images) > 0:
            all_reference_images.extend(reference_images)
        if reference_image and reference_image not in all_reference_images:
            all_reference_images.append(reference_image)

        # 如果有参考图片，构建多模态消息
        if all_reference_images:
            logger.debug(f"  添加 {len(all_reference_images)} 张参考图片到 chat 消息")
            content_parts = [{"type": "text", "text": prompt}]

            for idx, img_data in enumerate(all_reference_images):
                compressed_img = compress_image(img_data, max_size_kb=200)
                logger.debug(f"  参考图 {idx}: {len(img_data)} -> {len(compressed_img)} bytes")
                base64_image = base64.b64encode(compressed_img).decode('utf-8')
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                })

            user_content = content_parts

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": user_content}],
            "max_tokens": 4096,
            "temperature": 1.0
        }

        api_url = f"{self.base_url}{self.endpoint_type}"
        logger.info(f"Chat API 生成图片: {api_url}, model={model}")

        response = requests.post(api_url, headers=headers, json=payload, timeout=IMAGE_API_TIMEOUT)

        if response.status_code != 200:
            error_detail = response.text[:500]
            status_code = response.status_code

            if status_code == 401:
                raise Exception(
                    "❌ API Key 认证失败\n\n"
                    "【可能原因】\n"
                    "1. API Key 无效或已过期\n"
                    "2. API Key 格式错误\n\n"
                    "【解决方案】\n"
                    "在系统设置页面检查 API Key 是否正确"
                )
            elif status_code == 429:
                raise Exception(
                    "⏳ API 配额或速率限制\n\n"
                    "【解决方案】\n"
                    "1. 稍后再试\n"
                    "2. 检查 API 配额使用情况"
                )
            else:
                raise Exception(
                    f"❌ Chat API 请求失败 (状态码: {status_code})\n\n"
                    f"【错误详情】\n{error_detail[:300]}\n\n"
                    f"【请求地址】{api_url}\n"
                    f"【模型】{model}"
                )

        result = response.json()
        logger.debug(f"Chat API 响应: {str(result)[:500]}")

        # 解析响应
        if "choices" in result and len(result["choices"]) > 0:
            choice = result["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                content = choice["message"]["content"]

                if isinstance(content, str):
                    # Markdown 图片链接: ![xxx](url)
                    pattern = r'!\[.*?\]\((https?://[^\s\)]+)\)'
                    urls = re.findall(pattern, content)
                    if urls:
                        logger.info(f"从 Markdown 提取到 {len(urls)} 张图片，下载第一张...")
                        return self._download_image(urls[0])

                    # Markdown 图片 Base64: ![xxx](data:image/...)
                    base64_pattern = r'!\[.*?\]\((data:image\/[^;]+;base64,[^\s\)]+)\)'
                    base64_urls = re.findall(base64_pattern, content)
                    if base64_urls:
                        logger.info("从 Markdown 提取到 Base64 图片数据")
                        base64_data = base64_urls[0].split(",")[1]
                        return base64.b64decode(base64_data)

                    # 纯 Base64 data URL
                    if content.startswith("data:image"):
                        logger.info("检测到 Base64 图片数据")
                        base64_data = content.split(",")[1]
                        return base64.b64decode(base64_data)

                    # 纯 URL
                    if content.startswith("http://") or content.startswith("https://"):
                        logger.info("检测到图片 URL")
                        return self._download_image(content.strip())

        raise Exception(
            "❌ 无法从 Chat API 响应中提取图片数据\n\n"
            f"【响应内容】\n{str(result)[:500]}\n\n"
            "【可能原因】\n"
            "1. 该模型不支持图片生成\n"
            "2. 响应格式与预期不符\n"
            "3. 提示词被安全过滤\n\n"
            "【解决方案】\n"
            "1. 确认模型名称正确\n"
            "2. 修改提示词后重试"
        )

    def _download_image(self, url: str) -> bytes:
        """下载图片并返回二进制数据"""
        logger.info(f"下载图片: {url[:100]}...")
        try:
            response = requests.get(url, timeout=IMAGE_DOWNLOAD_TIMEOUT)
            if response.status_code == 200:
                logger.info(f"✅ 图片下载成功: {len(response.content)} bytes")
                return response.content
            else:
                raise Exception(f"下载图片失败: HTTP {response.status_code}")
        except requests.exceptions.Timeout:
            raise Exception("❌ 下载图片超时，请重试")
        except Exception as e:
            raise Exception(f"❌ 下载图片失败: {str(e)}")
