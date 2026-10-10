"""
LLM 配置 — DeepSeek API

DeepSeek 兼容 OpenAI 接口格式，使用 openai 库调用。
获取 API Key: https://platform.deepseek.com → 左侧 API Keys → 创建 API Key
"""

import os
import json

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# ================================================================
#  API Key 从环境变量或 .env 文件读取，请勿硬编码
#  在项目根目录创建 .env 文件，写入: DEEPSEEK_API_KEY=sk-xxx...
# ================================================================
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
# ================================================================

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"

_client = None


def get_llm_client():
    """
    获取 LLM 客户端实例。
    如果未配置 API Key 或 openai 库未安装，返回 None（调用方应回退到正则/模板）。
    """
    global _client
    if _client is not None:
        return _client

    if OpenAI is None:
        print("[LLM] openai 库未安装，回退到正则/模板模式")
        return None

    key = DEEPSEEK_API_KEY

    if not key:
        print("[LLM] 未配置 DEEPSEEK_API_KEY，回退到正则/模板模式")
        return None

    try:
        _client = OpenAI(api_key=key, base_url=DEEPSEEK_BASE_URL)
        print("[LLM] DeepSeek 客户端初始化成功")
        return _client
    except Exception as e:
        print(f"[LLM] 客户端初始化失败: {e}")
        return None


def llm_available():
    """检查 LLM 是否可用"""
    return get_llm_client() is not None


def llm_chat(system_prompt, user_prompt, temperature=0.3, max_tokens=2000):
    """
    调用 LLM 对话，返回文本内容。
    失败时返回 None（调用方应回退）。
    """
    client = get_llm_client()
    if client is None:
        return None

    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        content = response.choices[0].message.content
        return content
    except Exception as e:
        print(f"[LLM] 调用失败: {e}")
        return None


def llm_chat_json(system_prompt, user_prompt, temperature=0.1, max_tokens=2000):
    """
    调用 LLM 并解析 JSON 结果。
    返回解析后的 Python 对象，失败返回 None。
    """
    content = llm_chat(system_prompt, user_prompt, temperature, max_tokens)
    if content is None:
        return None

    # 清理可能的 markdown 代码块包裹
    content = content.strip()
    if content.startswith("```"):
        # 去掉 ```json 或 ``` 开头和 ``` 结尾
        lines = content.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines).strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # 尝试提取第一个 JSON 数组或对象
        import re
        arr_match = re.search(r'\[.*\]', content, re.DOTALL)
        if arr_match:
            try:
                return json.loads(arr_match.group())
            except json.JSONDecodeError:
                pass
        obj_match = re.search(r'\{.*\}', content, re.DOTALL)
        if obj_match:
            try:
                return json.loads(obj_match.group())
            except json.JSONDecodeError:
                pass
        print(f"[LLM] JSON 解析失败，原始内容: {content[:200]}")
        return None
