# _*_coding:utf-8_*_
"""
下载器中间件
"""


class DownloaderMiddleware(object):

    def prosess_request(self, request):

        print("DownloaderMiddleware: prosess_request")
        return request

    def prosess_response(self, response)

        print("DownloaderMiddleware: prosess_response")

        return response
