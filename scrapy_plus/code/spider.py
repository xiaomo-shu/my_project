# _*_coding:utf-8_*_
from ..http.request import Request
from ..item import Item
"""
提供初始请求
解析响应数据
"""


class Spider(object):

    start_url = 'http://www.baidu.com'

    def start_request(self):

        return Request(self.start_url)

    def parse(self, response):

        return Item(response.body)

