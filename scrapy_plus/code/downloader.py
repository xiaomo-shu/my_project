# _*_coding:utf-8_*_

"""
下载器模块：
 请求请求对象，发送请求获取响应数据。封装为Response对象返回
"""
import requests
from ..http.response import Response


class Downloader(object):

    def get_response(self, request):
        if request.method.upper() == 'GET':
            res = requests.get(request.url, headers=request.headers, params=request.params, cookies=request.cookies)
        elif request.method.upper() == 'POST':
            res = requests.post(request.url, headers=request.headers, data=request.data, cookies=request.cookies)
        else:
            raise Exception('暂时只提供get和post方法')

        return Response(res.url, res.headers, res.status_code, res.content)
