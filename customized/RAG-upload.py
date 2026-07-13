import json

import requests


#鉴权部分
from datetime import datetime
from wsgiref.handlers import format_date_time
from time import mktime
import hashlib
import base64
import hmac
from urllib.parse import urlencode
from urllib.parse import urlparse


# build  auth request url
# method="GET"  if  ws(s) or GET;
# method="POST" if POST
def assemble_auth_url(request_url, method, api_key, api_secret):
    u = urlparse(request_url)
    host = u.hostname
    path = u.path
    now = datetime.now()
    date = format_date_time(mktime(now.timetuple()))
    # print(date)
    # date = "Thu, 12 Dec 2019 01:57:27 GMT"
    signature_origin = "host: {}\ndate: {}\n{} {} HTTP/1.1".format(host, date, method, path)
    # print(signature_origin)
    signature_sha = hmac.new(api_secret.encode('utf-8'), signature_origin.encode('utf-8'),
                             digestmod=hashlib.sha256).digest()
    signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')
    authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
        api_key, "hmac-sha256", "host date request-line", signature_sha)
    authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
    # print(authorization_origin)
    values = {
        "host": host,
        "date": date,
        "authorization": authorization
    }

    return request_url + "?" + urlencode(values)



#知识库管理

class knowledgeBase:
    def __init__(self,appid,apikey,apisecret,name):
        self.appid = appid
        self.apikey = apikey
        self.apisecret= apisecret
        self.name = name


    def createBase(self):
        url = 'https://sparkcube-api.xf-yun.com/v1/knowledge/create'
        authurl = assemble_auth_url(url,'POST',self.apikey,self.apisecret)
        header = {
            'x-appid':self.appid
        }
        body={
            "kb_id":self.name
        }
        # data = f"kb_id={self.name}"
        response = requests.post(authurl,data= body,headers= header).text

        return response


# 文件管理
class FileManage:
    def __init__(self,appid,apikey,apisecret,path):
        self.appid = appid
        self.apikey = apikey
        self.apisecret= apisecret
        self.path = path

    #文件上传
    def fileUpload(self,name):
        url = 'https://sparkcube-api.xf-yun.com/v1/files'
        authurl = assemble_auth_url(url,'POST',self.apikey,self.apisecret)
        header = {
            "x-appid":self.appid
        }
        data = {
            "purpose":"file-extract",
            "kb_id":name
        }
        files = {
            'file': (self.path, open(self.path, 'rb'), 'text/plain')
        }
        response = requests.post(authurl,data= data,files=files,headers= header).text

        return response

    def filedel(self,fileid):
        url = f'https://sparkcube-api.xf-yun.com/v1/files/{fileid}'
        authurl = assemble_auth_url(url,"DELETE",self.apikey,self.apisecret)
        header ={
            "x-appid": self.appid
        }
        authurl = url +"?purpose=file-extract"
        response = requests.delete(url,headers=header).text

        return response

if __name__ == '__main__':

    appid ="XXXXXXXX"
    apikey ="XXXXXXXXXXXXXXXXXXXXXXXX"
    apisecret ="XXXXXXXXXXXXXXXXXXXXXXXX"
    name ="XXXXXXXX_longctx_repo_XXX"  #  知识库id示例   XXXXXXXX建议用appid区分,XXX为编号


    # #step1:创建知识库对象
    # kb = knowledgeBase(appid,apikey,apisecret,name)
    #
    # # 创建知识库
    # resp = kb.createBase()

    #step2:创建文件管理对象
    fm = FileManage(appid,apikey,apisecret,"data/2022中国大模型发展白皮书.pdf")

    # 文档上传
    resp = fm.fileUpload(name)
    
    

    print(resp)