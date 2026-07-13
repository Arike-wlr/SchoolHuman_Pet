# coding: utf-8
import SparkApi2
import time
#以下密钥信息从控制台获取

appid = "XXXXXXXX"     #填写控制台中获取的 APPID 信息
api_secret = "XXXXXXXXXXXXXXXXXXXXXXXX"   #填写控制台中获取的 APISecret 信息
api_key ="XXXXXXXXXXXXXXXXXXXXXXXX"    #填写控制台中获取的 APIKey 信息


# 配置模型版本
domain = "max"    # 多语种

#云端环境的服务地址

Spark_url = "wss://sparkcube-api.xf-yun.com/v1/customize"  # 正式服务地址


# 读取txt文件内容
def read_txt_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return content

text =[
        # {"role":"system","content": "你叫刘希，性别： 男；爱好：篮球 ，当前司职得分后卫；你的梦想：打进NBA,夺得总冠军，请以这样的身份与用户展开对话"}
    ]

# length = 0

def getText(role,content):
    jsoncon = {}
    jsoncon["role"] = role
    jsoncon["content"] = content
    text.append(jsoncon)
    # print(text)
    return text



def getlength(text):
    length = 0
    for content in text:
        temp = content["content"]
        leng = len(temp)
        length += leng
    # print("content长度：",length)
    return length

def checklen(text):
    while (getlength(text) > 1280000):
        del text[0]
    return text
    


if __name__ == '__main__':



        # 问答query 有两种方式：
        # 1、如果基于通用或联网知识问答，则不需要传type 为file的数据，文档上传见RAG-upload.py
        # 2、如果需要同时基于私有数据问答，则需要同时上传type为file的数据

        query = [
                    # {
                    #     "type": "file",
                    #     "file": [    # fileID 列表，支持同时提问多个文档，如需向文档提问，请先通过接口创建知识库，并上传文档
                    #         "f_e01d46b7_f122_4bc5_ab79_38b7770a3baf",  # 每个fileid 对应一个文档
                    #         # "file_id2"
                    #     ]
                    # },
                    {
                        "type": "text",
                        "text": "如何去除甲醛"
                    }
                ]

        print("星火:",end = "")

        SparkApi2.main(appid,api_key,api_secret,Spark_url,domain,query)
        print(SparkApi2.answer)
        getText("assistant",SparkApi2.answer)
