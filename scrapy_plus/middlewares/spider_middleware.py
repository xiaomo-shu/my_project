# _*_coding:utf-8_*_

"""
爬虫中间件
"""


class SpiderMiddleware(object):

    def prosess_request(self, request):

        print("SpiderMiddleware: prosess_request")

        return request

    def prosess_response(self, response):

        print("SpiderMiddleware: prosess_response")
    