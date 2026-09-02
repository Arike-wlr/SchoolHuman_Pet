import _thread as thread
import base64
import datetime
import hashlib
import hmac
import json
import time
from urllib.parse import urlparse
import ssl
from datetime import datetime
from time import mktime
from urllib.parse import urlencode

import websocket

def format_date_time(timestamp):
    return datetime.utcfromtimestamp(timestamp).strftime('%a, %d %b %Y %H:%M:%S GMT')

class Ws_Param(object):
    def __init__(self, APPID, APIKey, APISecret, Spark_url):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.host = urlparse(Spark_url).netloc
        self.path = urlparse(Spark_url).path
        self.Spark_url = Spark_url

    def create_url(self):
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        signature_origin = "host: " + self.host + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + self.path + " HTTP/1.1"

        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()

        signature_sha_base64 = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = f'api_key="{self.APIKey}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'

        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')

        v = {
            "authorization": authorization,
            "date": date,
            "host": self.host
        }
        url = self.Spark_url + '?' + urlencode(v)
        return url


def on_error(ws, error):
    print("### error:", error)


def on_close(ws, one, two):
    pass


def on_open(ws):
    thread.start_new_thread(run, (ws,))


def run(ws, *args):
    data = json.dumps(gen_params(
        appid=ws.appid,
        domain=ws.domain,
        messages=ws.messages,
        functions=getattr(ws, 'functions', None)
    ))
    ws.send(data)


def on_message(ws, message):
    data = json.loads(message)
    code = data['header']['code']
    if code != 0:
        print(f'请求错误: {code}, {data}')
        if ws.on_response:
            ws.on_response(f"Error: {code}", finished=True)
        ws.close()
        return

    # === 方式B：函数调用（Tool Call）处理 ===
    # 服务端要求调用工具时，不返回 choices 而是 function_call / plugin_call
    payload = data.get('payload', {})
    if 'function_call' in payload or 'plugin_call' in payload:
        call_info = payload.get('function_call') or payload.get('plugin_call')
        # 通知外部执行本地查询
        if hasattr(ws, 'on_tool_call') and ws.on_tool_call:
            ws.on_tool_call(call_info)
        # 不关闭连接，等待第二轮
        return

    # === 原有 RAG 插件处理 ===
    if 'plugins' in data['payload']:
        text_list = data['payload']['plugins']['text']
        search_refer = text_list[0]
        refer_content = search_refer['content']
        refer_list = json.loads(refer_content)
        ref_text = "参考内容：\n"
        for line in refer_list:
            num = line['index']
            url = line['url']
            title = line['title']
            ref_text += str(num) + "、" + title + "[ " + url + " ]\n"
        if ws.on_response:
            ws.on_response(ref_text, finished=False)
    else:
        sid = data["header"]["sid"]
        choices = data["payload"]["choices"]
        status = choices["status"]
        content = choices["text"][0]["content"]
        if ws.on_response:
            ws.on_response(content, finished=(status == 2))
        if status == 2:
            ws.close()


def _to_spark_text(messages):
    """将 OpenAI-style messages / 字符串 / 其他格式统一转为 Spark message.text 格式。"""
    if isinstance(messages, list):
        converted = []
        for msg in messages:
            if isinstance(msg, dict):
                if "type" in msg and "text" in msg:
                    # 已是 Spark 格式
                    converted.append(msg)
                elif "content" in msg:
                    # OpenAI 格式: role/content -> Spark type/text
                    converted.append({"type": "text", "text": msg["content"]})
                elif "text" in msg:
                    converted.append({"type": "text", "text": msg["text"]})
                else:
                    converted.append({"type": "text", "text": str(msg)})
            elif isinstance(msg, str):
                converted.append({"type": "text", "text": msg})
            else:
                converted.append({"type": "text", "text": str(msg)})
        return converted
    if isinstance(messages, str):
        return [{"type": "text", "text": messages}]
    return messages

def gen_params(appid, domain, messages, functions=None):
    payload = {
        "message": {
            "text": _to_spark_text(messages)
        }
    }
    if functions is not None:
        payload["functions"] = functions
    data = {
        "header": {
            "app_id": appid,
            "uid": "1234"
        },
        "parameter": {
            "chat": {
                "domain": domain,
                "temperature": 0.99,
                "max_tokens": 4 * 1024,
                "top_k": 6,
            }
        },
        "payload": payload
    }
    return data


def send_followup(ws, messages):
    """第二轮：向已打开的 WebSocket 发送后续消息（用于 Function Call 结果回传）。"""
    data = json.dumps(gen_params(
        appid=ws.appid,
        domain=ws.domain,
        messages=messages,
        functions=getattr(ws, 'functions', None)
    ))
    ws.send(data)


def main(appid, api_key, api_secret, Spark_url, domain, messages, on_response=None, functions=None, on_tool_call=None):
    wsParam = Ws_Param(appid, api_key, api_secret, Spark_url)
    websocket.enableTrace(False)
    wsUrl = wsParam.create_url()
    ws = websocket.WebSocketApp(wsUrl, on_message=on_message, on_error=on_error, on_close=on_close, on_open=on_open)
    ws.appid = appid
    ws.messages = messages
    ws.domain = domain
    ws.on_response = on_response
    ws.on_tool_call = on_tool_call
    ws.functions = functions
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})