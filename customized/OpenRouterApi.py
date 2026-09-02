"""OpenRouter 适配层（OpenAI 兼容格式，支持 function calling + 流式回复）。
调用方式：from OpenRouterApi import main; main(api_key, model, messages, ...)
"""
import requests, json, sys, time

# 默认免费模型（可替换）
DEFAULT_MODEL = "openrouter/free"
BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

class OpenRouterWorker:
    def __init__(self, api_key, model=DEFAULT_MODEL):
        self.api_key = api_key
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def chat(self, messages, tools=None, on_chunk=None, on_done=None):
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096,
            "stream": True
        }
        if tools is not None:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        try:
            r = requests.post(BASE_URL, headers=self.headers, json=payload, stream=True, timeout=60)
            if r.status_code != 200:
                err = r.text[:300]
                print(f"[OpenRouter] HTTP {r.status_code}: {err}")
                return f"API Error: {r.status_code}"
            content = ""
            tool_call_pending = None
            for line in r.iter_lines():
                if not line:
                    continue
                line = line.decode('utf-8', errors='ignore')
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                    except:
                        continue
                    delta = obj.get("choices", [{}])[0].get("delta", {})
                    chunk_text = delta.get("content") or ""
                    if chunk_text:
                        content += chunk_text
                        if on_chunk:
                            on_chunk(chunk_text, finished=False)
                    # 检测 function_call（方法 B）
                    tool_calls = delta.get("tool_calls")
                    if tool_calls:
                        for tc in tool_calls:
                            if tc.get("function"):
                                tool_call_pending = tc.get("function")
            if on_chunk:
                on_chunk(content, finished=True)
            # 如果第二轮需要：业务层处理 tool_call 并 callback
            return content
        except Exception as e:
            print(f"[OpenRouter] Exception: {e}")
            return f"Request Exception: {e}"


def main(api_key, model=DEFAULT_MODEL, messages=None, on_response=None, functions=None):
    """封装调用，兼容 show_pet.py ChatWorker 接口风格。"""
    worker = OpenRouterWorker(api_key, model)
    # OpenAI 格式的 messages（已由 show_pet 构造）
    # functions → OpenAI tools
    tools = None
    if functions is not None:
        # 方法 B：工具声明直接作为 OpenAI tools 传入
        if isinstance(functions, dict) and "name" in functions:
            tools = [{"type": "function", "function": functions}]
        elif isinstance(functions, list):
            tools = [{"type": "function", "function": f} for f in functions]
        else:
            tools = [{"type": "function", "function": functions}]

    def chunk_cb(text, finished):
        if on_response:
            on_response(text, finished=finished)

    result = worker.chat(messages, tools=tools, on_chunk=chunk_cb)
    return result
