# _*_coding:utf-8_*_
"""
封装响应数据
"""


class Response(object):
    
    def __init__(self, url, headers, status_code, body)
    self.url = url 
    self.headers = headers
    self.status_code = status_code
    self.body = body