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
    data = json.dumps(gen_params(appid=ws.appid, domain=ws.domain, messages=ws.messages))
    ws.send(data)


def on_message(ws, message):
    data = json.loads(message)
    code = data['header']['code']
    if code != 0:
        print(f'请求错误: {code}, {data}')
        if ws.on_response:
            ws.on_response(f"Error: {code}", finished=True)
        ws.close()
    else:
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


def gen_params(appid, domain, messages):
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
        "payload": {
            "message": {
                "text": messages
            }
        }
    }
    return data


def main(appid, api_key, api_secret, Spark_url, domain, messages, on_response=None):
    wsParam = Ws_Param(appid, api_key, api_secret, Spark_url)
    websocket.enableTrace(False)
    wsUrl = wsParam.create_url()
    ws = websocket.WebSocketApp(wsUrl, on_message=on_message, on_error=on_error, on_close=on_close, on_open=on_open)
    ws.appid = appid
    ws.messages = messages
    ws.domain = domain
    ws.on_response = on_response
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
