"""
配置管理相关 API 路由

包含功能：
- 获取当前配置
- 更新配置
- 测试服务商连接
"""

import logging
from copy import deepcopy
from pathlib import Path
from flask import Blueprint, request, jsonify
from backend.config import get_config_service
from backend.middleware import require_auth
from .utils import prepare_providers_for_response

logger = logging.getLogger(__name__)
config_service = get_config_service()

# 配置标识（保留 Path 形式，兼容现有调用签名）
CONFIG_DIR = Path(__file__).parent.parent.parent
IMAGE_CONFIG_PATH = CONFIG_DIR / "image_providers.yaml"
TEXT_CONFIG_PATH = CONFIG_DIR / "text_providers.yaml"
SEARCH_CONFIG_PATH = CONFIG_DIR / "search_providers.yaml"

_CONFIG_NAME_BY_PATH = {
    IMAGE_CONFIG_PATH: "image_providers",
    TEXT_CONFIG_PATH: "text_providers",
    SEARCH_CONFIG_PATH: "search_providers",
}


def create_config_blueprint():
    """创建配置路由蓝图（工厂函数，支持多次调用）"""
    config_bp = Blueprint('config', __name__)

    # ==================== 配置读写 ====================

    @config_bp.route('/config', methods=['GET'])
    def get_config():
        """
        获取当前配置

        返回：
        - success: 是否成功
        - config: 配置对象
          - text_generation: 文本生成配置
          - image_generation: 图片生成配置
        - search: 通用搜索配置
        """
        try:
            # 读取图片生成配置
            image_config = _read_config(IMAGE_CONFIG_PATH, {
                'active_provider': 'google_genai',
                'providers': {}
            })

            # 读取文本生成配置
            text_config = _read_config(TEXT_CONFIG_PATH, {
                'active_provider': 'google_gemini',
                'providers': {}
            })

            search_config = config_service.load_search_providers_config()
            search_providers = search_config.get("providers", {})
            search_response = {
                "active_provider": search_config.get("active_provider", "bing"),
                "providers": _prepare_search_providers_for_response(search_providers),
            }

            return jsonify({
                "success": True,
                "config": {
                    "text_generation": {
                        "active_provider": text_config.get('active_provider', ''),
                        "providers": prepare_providers_for_response(
                            text_config.get('providers', {})
                        )
                    },
                    "image_generation": {
                        "active_provider": image_config.get('active_provider', ''),
                        "providers": prepare_providers_for_response(
                            image_config.get('providers', {})
                        )
                    },
                    "search": search_response
                }
            })

        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"获取配置失败: {str(e)}"
            }), 500

    @config_bp.route('/config', methods=['POST'])
    @require_auth
    def update_config():
        """
        更新配置

        请求体：
        - image_generation: 图片生成配置（可选）
        - text_generation: 文本生成配置（可选）

        返回：
        - success: 是否成功
        - message: 结果消息
        """
        try:
            data = request.get_json()
            if not isinstance(data, dict):
                return jsonify({
                    "success": False,
                    "error": "请求体必须为 JSON 对象"
                }), 400

            # 更新图片生成配置
            if 'image_generation' in data:
                _update_provider_config(
                    IMAGE_CONFIG_PATH,
                    data['image_generation']
                )

            # 更新文本生成配置
            if 'text_generation' in data:
                _update_provider_config(
                    TEXT_CONFIG_PATH,
                    data['text_generation']
                )

            # 更新通用搜索配置
            if 'search' in data:
                _update_search_config(data['search'])

            # 清除配置缓存，确保下次使用时读取新配置
            _clear_config_cache()

            return jsonify({
                "success": True,
                "message": "配置已保存"
            })

        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"更新配置失败: {str(e)}"
            }), 500

    # ==================== 连接测试 ====================

    @config_bp.route('/config/test', methods=['POST'])
    @require_auth
    def test_connection():
        """
        测试服务商连接

        请求体：
        - type: 服务商类型（google_genai/google_gemini/openai_compatible/image_api/firecrawl/exa/tavily/perplexity/bing）
        - provider_name: 服务商名称（用于从配置读取 API Key）
        - api_key: API Key（可选，若不提供则从配置读取）
        - base_url: Base URL（可选）
        - model: 模型名称（可选）

        返回：
        - success: 是否成功
        - message: 测试结果消息
        """
        try:
            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                return jsonify({"success": False, "error": "请求体必须为 JSON 对象"}), 400
            provider_type = str(data.get('type') or '').strip().lower()
            provider_name = data.get('provider_name')

            if not provider_type:
                return jsonify({"success": False, "error": "缺少 type 参数"}), 400

            # 构建配置
            config = {
                'api_key': data.get('api_key'),
                'base_url': data.get('base_url'),
                'model': data.get('model'),
                'endpoint_type': data.get('endpoint_type')
            }

            # 如果没有提供 api_key，从配置文件读取
            if not config['api_key'] and provider_name:
                config = _load_provider_config(provider_type, provider_name, config)

            if not config['api_key'] and provider_type not in {'firecrawl', 'bing'}:
                return jsonify({"success": False, "error": "API Key 未配置"}), 400

            # 根据类型执行测试
            result = _test_provider_connection(provider_type, config)
            return jsonify(result), 200 if result['success'] else 400

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    return config_bp


# ==================== 辅助函数 ====================

def _mask_api_key(api_key: str) -> str:
    api_key = (api_key or "").strip()
    if not api_key:
        return ""
    if len(api_key) > 8:
        return api_key[:8] + "****"
    return "****"


def _prepare_search_providers_for_response(providers: dict) -> dict:
    """搜索服务商脱敏输出。"""
    if not isinstance(providers, dict):
        return {}

    response = {}
    for name, provider in providers.items():
        if not isinstance(provider, dict):
            continue
        item = provider.copy()
        api_key = (item.get("api_key") or "").strip()
        item["api_key_masked"] = _mask_api_key(api_key)
        item["_has_api_key"] = bool(api_key)
        item.pop("api_key", None)
        response[name] = item
    return response


def _read_config(path: Path, default: dict) -> dict:
    """读取配置（由配置服务决定是 YAML 还是 Supabase）。"""

    config_name = _CONFIG_NAME_BY_PATH.get(path)
    if config_name == "image_providers":
        data = config_service.load_image_providers_config()
    elif config_name == "text_providers":
        data = config_service.load_text_providers_config()
    elif config_name == "search_providers":
        data = config_service.load_search_providers_config()
    else:
        logger.warning(f"未知配置路径，回退默认值: {path}")
        return deepcopy(default)

    if not isinstance(data, dict):
        return deepcopy(default)
    return deepcopy(data)


def _write_config(path: Path, config: dict):
    """写入配置（由配置服务决定是 YAML 还是 Supabase）。"""

    config_name = _CONFIG_NAME_BY_PATH.get(path)
    if config_name == "image_providers":
        config_service.save_image_providers_config(config)
        return
    if config_name == "text_providers":
        config_service.save_text_providers_config(config)
        return
    if config_name == "search_providers":
        config_service.save_search_providers_config(config)
        return

    raise ValueError(f"不支持写入的配置路径: {path}")


def _update_provider_config(config_path: Path, new_data: dict):
    """
    更新服务商配置

    Args:
        config_path: 配置文件路径
        new_data: 新的配置数据
    """
    # 读取现有配置
    existing_config = _read_config(config_path, {'providers': {}})

    # 更新 active_provider
    if 'active_provider' in new_data:
        existing_config['active_provider'] = new_data['active_provider']

    # 更新 providers
    if 'providers' in new_data:
        existing_providers = existing_config.get('providers', {})
        new_providers = new_data['providers']

        for name, new_provider_config in new_providers.items():
            # 如果新配置的 api_key 是空的，保留原有的
            if new_provider_config.get('api_key') in [True, False, '', None]:
                if name in existing_providers and existing_providers[name].get('api_key'):
                    new_provider_config['api_key'] = existing_providers[name]['api_key']
                else:
                    new_provider_config.pop('api_key', None)

            # 移除不需要保存的字段
            new_provider_config.pop('api_key_env', None)
            new_provider_config.pop('api_key_masked', None)

        existing_config['providers'] = new_providers

    # 保存配置
    _write_config(config_path, existing_config)


def _clear_config_cache():
    """清除配置缓存"""
    try:
        config_service.reload()
    except Exception:
        pass

    try:
        from backend.services.image import reset_image_service
        reset_image_service()
    except Exception:
        pass


def _update_search_config(new_data: dict):
    """更新通用搜索配置。"""
    if not isinstance(new_data, dict):
        return

    existing_config = config_service.load_search_providers_config()
    existing_providers = existing_config.get("providers", {})

    if "providers" in new_data and isinstance(new_data["providers"], dict):
        for name, incoming in new_data["providers"].items():
            if not name or not isinstance(incoming, dict):
                continue

            current = existing_providers.get(name, {})
            merged = current.copy()
            merged.update(incoming)
            merged["type"] = (merged.get("type") or name).strip().lower()

            # 空 api_key 表示保留旧值
            incoming_api_key = incoming.get("api_key")
            if incoming_api_key in (None, "", True, False):
                if current.get("api_key"):
                    merged["api_key"] = current.get("api_key")
                else:
                    merged.pop("api_key", None)
            else:
                merged["api_key"] = str(incoming_api_key).strip()

            # 脱敏/临时字段不落库
            merged.pop("api_key_masked", None)
            merged.pop("api_key_env", None)
            merged.pop("_has_api_key", None)

            existing_providers[name] = merged

    if "active_provider" in new_data:
        existing_config["active_provider"] = str(new_data.get("active_provider") or "").strip()

    existing_config["providers"] = existing_providers
    config_service.save_search_providers_config(existing_config)


def _load_provider_config(provider_type: str, provider_name: str, config: dict) -> dict:
    """
    从配置文件加载服务商配置

    Args:
        provider_type: 服务商类型
        provider_name: 服务商名称
        config: 当前配置（会被合并）

    Returns:
        dict: 合并后的配置
    """
    # 搜索服务商配置独立保存（firecrawl/exa/tavily/perplexity/bing）
    if provider_type in ['firecrawl', 'exa', 'tavily', 'perplexity', 'bing']:
        search_config = config_service.load_search_providers_config()
        providers = search_config.get("providers", {})
        saved = providers.get(provider_name) or providers.get(provider_type) or {}

        if not config.get('api_key'):
            config['api_key'] = saved.get('api_key')
        if not config.get('base_url'):
            config['base_url'] = saved.get('base_url')
        if not config.get('enabled'):
            config['enabled'] = saved.get('enabled')
        if not config.get('type'):
            config['type'] = saved.get('type') or provider_type
        if not config.get('model'):
            config['model'] = saved.get('model')
        return config

    # 确定配置文件路径
    if provider_type in ['openai_compatible', 'google_gemini']:
        config_path = TEXT_CONFIG_PATH
    else:
        config_path = IMAGE_CONFIG_PATH

    yaml_config = _read_config(config_path, {"providers": {}})
    providers = yaml_config.get("providers", {})

    if provider_name in providers:
        saved = providers[provider_name]
        config["api_key"] = saved.get("api_key")

        if not config["base_url"]:
            config["base_url"] = saved.get("base_url")
        if not config["model"]:
            config["model"] = saved.get("model")
        if not config.get("endpoint_type"):
            config["endpoint_type"] = saved.get("endpoint_type")

    return config


def _test_provider_connection(provider_type: str, config: dict) -> dict:
    """
    测试服务商连接

    Args:
        provider_type: 服务商类型
        config: 服务商配置

    Returns:
        dict: 测试结果
    """
    test_prompt = "请回复'你好，渲染AI'"

    if provider_type == 'google_genai':
        return _test_google_genai(config)

    elif provider_type == 'google_gemini':
        return _test_google_gemini(config, test_prompt)

    elif provider_type == 'openai_compatible':
        return _test_openai_compatible(config, test_prompt)

    elif provider_type == 'image_api':
        return _test_image_api(config)

    elif provider_type == 'dashscope':
        return _test_dashscope(config)

    elif provider_type == 'modelscope':
        return _test_modelscope(config)

    elif provider_type == 'replicate':
        return _test_replicate(config)

    elif provider_type == 'firecrawl':
        return _test_firecrawl(config)

    elif provider_type == 'exa':
        return _test_exa(config)

    elif provider_type == 'tavily':
        return _test_tavily(config)

    elif provider_type == 'perplexity':
        return _test_perplexity(config)

    elif provider_type == 'bing':
        return _test_bing(config)

    else:
        raise ValueError(f"不支持的类型: {provider_type}")


def _test_google_genai(config: dict) -> dict:
    """测试 Google GenAI 图片生成服务"""
    from google import genai

    if config.get('base_url'):
        client = genai.Client(
            api_key=config['api_key'],
            http_options={
                'base_url': config['base_url'],
                'api_version': 'v1beta'
            },
            vertexai=False
        )
        # 测试列出模型
        try:
            list(client.models.list())
            return {
                "success": True,
                "message": "连接成功！仅代表连接稳定，不确定是否可以稳定支持图片生成"
            }
        except Exception as e:
            raise Exception(f"连接测试失败: {str(e)}")
    else:
        return {
            "success": True,
            "message": "Vertex AI 无法通过 API Key 测试连接（需要 OAuth2 认证）。请在实际生成图片时验证配置是否正确。"
        }


def _test_google_gemini(config: dict, test_prompt: str) -> dict:
    """测试 Google Gemini 文本生成服务"""
    from google import genai

    if config.get('base_url'):
        client = genai.Client(
            api_key=config['api_key'],
            http_options={
                'base_url': config['base_url'],
                'api_version': 'v1beta'
            },
            vertexai=False
        )
    else:
        client = genai.Client(
            api_key=config['api_key'],
            vertexai=True
        )

    model = config.get('model') or 'gemini-2.0-flash-exp'
    response = client.models.generate_content(
        model=model,
        contents=test_prompt
    )
    result_text = response.text if hasattr(response, 'text') else str(response)

    return _check_response(result_text)


def _test_openai_compatible(config: dict, test_prompt: str) -> dict:
    """测试 OpenAI 兼容接口"""
    import requests

    if config.get('base_url'):
        base_url = config['base_url'].rstrip('/')
        if base_url.endswith('/v1'):
            base_url = base_url[:-3]
    else:
        base_url = 'https://api.openai.com'
    url = f"{base_url}/v1/chat/completions"

    payload = {
        "model": config.get('model') or 'gpt-3.5-turbo',
        "messages": [{"role": "user", "content": test_prompt}],
        "max_tokens": 50
    }

    response = requests.post(
        url,
        headers={
            'Authorization': f"Bearer {config['api_key']}",
            'Content-Type': 'application/json'
        },
        json=payload,
        timeout=30
    )

    if response.status_code != 200:
        raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")

    result = response.json()
    result_text = result['choices'][0]['message']['content']

    return _check_response(result_text)


def _test_dashscope(config: dict) -> dict:
    """测试 DashScope SDK 图片生成服务"""
    from dashscope import MultiModalConversation
    import dashscope

    base_url = (config.get('base_url') or '').strip().rstrip('/')
    if base_url:
        marker = '/api/v1'
        idx = base_url.find(marker)
        if idx != -1:
            base_url = base_url[:idx + len(marker)]
        elif base_url.endswith('/api'):
            base_url = base_url + '/v1'
        else:
            base_url = base_url + '/api/v1'

    old_base_url = getattr(dashscope, 'base_http_api_url', None)
    if base_url:
        dashscope.base_http_api_url = base_url

    try:
        response = MultiModalConversation.call(
            api_key=config['api_key'],
            model=config.get('model') or 'qwen-image-max',
            messages=[
                {
                    "role": "user",
                    "content": [{"text": "画一只小猫"}],
                }
            ],
            result_format='message',
            stream=False,
            watermark=False,
            prompt_extend=True,
            size='1328*1328',
        )
    finally:
        if base_url:
            dashscope.base_http_api_url = old_base_url

    if response.status_code == 200:
        return {
            "success": True,
            "message": "连接成功！仅代表连接稳定，不确定是否可以稳定支持图片生成"
        }

    raise Exception(f"HTTP {response.status_code}: {getattr(response, 'message', '')}")


def _test_image_api(config: dict) -> dict:
    """测试图片 API 连接"""
    import requests

    if config.get('base_url'):
        base_url = config['base_url'].rstrip('/')
        if base_url.endswith('/v1'):
            base_url = base_url[:-3]
    else:
        base_url = 'https://api.openai.com'
    url = f"{base_url}/v1/models"

    response = requests.get(
        url,
        headers={'Authorization': f"Bearer {config['api_key']}"},
        timeout=30
    )

    if response.status_code == 200:
        return {
            "success": True,
            "message": "连接成功！仅代表连接稳定，不确定是否可以稳定支持图片生成"
        }
    else:
        raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")


def _test_modelscope(config: dict) -> dict:
    """测试 ModelScope 图片 API 连接"""
    import requests

    base_url = (config.get('base_url') or 'https://api-inference.modelscope.cn').rstrip('/')
    url = f"{base_url}/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
        "X-ModelScope-Async-Mode": "true",
    }
    payload = {
        "model": config.get('model') or 'Tongyi-MAI/Z-Image-Turbo',
        "prompt": "test",
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    if response.status_code != 200:
        raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")

    data = response.json()
    if not data.get("task_id"):
        raise Exception(f"ModelScope 返回异常: {str(data)[:200]}")

    return {
        "success": True,
        "message": f"连接成功！任务提交成功（task_id={data.get('task_id')}）"
    }


def _test_replicate(config: dict) -> dict:
    """测试 Replicate API Key 与模型访问权限。"""
    try:
        import replicate
    except Exception as e:
        raise Exception(f"未安装 replicate 依赖: {e}")

    client = replicate.Client(api_token=config['api_key'])
    model_id = config.get('model') or (
        'prunaai/z-image-turbo:'
        '0870559624690b3709350177b9d521d84e54d297026d725358b8f73193429e91'
    )
    model_name = model_id.split(':', 1)[0]

    try:
        model = client.models.get(model_name)
    except Exception as e:
        raise Exception(f"连接失败或模型不可访问: {e}")

    return {
        "success": True,
        "message": f"连接成功！模型可访问：{model.owner}/{model.name}"
    }


def _test_firecrawl(config: dict) -> dict:
    """测试 Firecrawl 连接。"""
    from backend.services.search_service import test_provider

    result = test_provider("firecrawl", {
        "type": "firecrawl",
        "api_key": config.get("api_key"),
        "base_url": config.get("base_url"),
    })
    if not result.get("success"):
        raise Exception(result.get("message") or "Firecrawl 连接失败")
    return result


def _test_exa(config: dict) -> dict:
    """测试 Exa 连接。"""
    from backend.services.search_service import test_provider

    result = test_provider("exa", {
        "type": "exa",
        "api_key": config.get("api_key"),
        "base_url": config.get("base_url"),
    })
    if not result.get("success"):
        raise Exception(result.get("message") or "Exa 连接失败")
    return result


def _test_tavily(config: dict) -> dict:
    """测试 Tavily 连接。"""
    from backend.services.search_service import test_provider

    result = test_provider("tavily", {
        "type": "tavily",
        "api_key": config.get("api_key"),
        "base_url": config.get("base_url"),
    })
    if not result.get("success"):
        raise Exception(result.get("message") or "Tavily 连接失败")
    return result


def _test_perplexity(config: dict) -> dict:
    """测试 Perplexity 连接。"""
    from backend.services.search_service import test_provider

    result = test_provider("perplexity", {
        "type": "perplexity",
        "api_key": config.get("api_key"),
        "base_url": config.get("base_url"),
        "model": config.get("model"),
    })
    if not result.get("success"):
        raise Exception(result.get("message") or "Perplexity 连接失败")
    return result


def _test_bing(config: dict) -> dict:
    """测试 Bing 抓取能力。"""
    from backend.services.search_service import test_provider

    result = test_provider("bing", {
        "type": "bing",
        "base_url": config.get("base_url"),
    })
    if not result.get("success"):
        raise Exception(result.get("message") or "Bing 连接失败")
    return result


def _check_response(result_text: str) -> dict:
    """检查响应是否符合预期"""
    if "你好" in result_text and "渲染AI" in result_text:
        return {
            "success": True,
            "message": f"连接成功！响应: {result_text[:100]}"
        }
    else:
        return {
            "success": True,
            "message": f"连接成功，但响应内容不符合预期: {result_text[:100]}"
        }
