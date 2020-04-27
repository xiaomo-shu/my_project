# _*_coding:utf-8_*_
"""
封装请求数据
"""

class Request(object):

    def __init__(self, url, method="GET", headers={}, data={}, param={}, cookies={})
    self.url = url 
    self.method = method
    self.headers = headers
    self.data = data
    self.param = param
    self.cookies = cookies
    