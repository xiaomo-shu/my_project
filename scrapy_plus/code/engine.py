# _*_coding:utf-8_*_

"""
引擎模块：负责协调各个模块
1.框架启动
2.框架运行流程

思路：
 1.对各个模块进行初始化
 2.启动爬虫，实现运行逻辑
"""
from pipline import Pipeline
from downloader import Downloader
from .scheduler import Scheduler
from .spider import Spider
from ..http.request import Request
from ..http.response import Response
from ..item import Item
from ..middlewares.downloader_middleware import DownloaderMiddleware
from ..middlewares.spider_middleware import SpiderMiddleware


class Engine(object):
    
    def __init__(self):
        # 初始化四大核心模块
        self.pipline = Pipeline()
        self.downloader = Downloader()
        self.spider = Spider()
        self.scheduler = Scheduler()
        # 初始化中间件
        self.downloader_middleware = DownloaderMiddleware()
        self.spider_middleware = SpiderMiddleware()

    def start(self):
        # 对外提供的启动接口
        # 为了代码的可扩展性，在内部封装一个私有方法来实现核心逻辑
        self._start()

    def _start(self):
        # 调用爬虫的start_request方法获取初始请求对象
        request = self.spider.start_request()
        # 把请求添加到调度器中之前要经过爬虫中间件
        request = self.spider_middleware.prosess_request(request)
        # 把该请求添加到调度器中
        self.scheduler.add_request(request)
        # 从调度器中获取请求对象
        request = self.scheduler.get_request()
        # 把请求交给下载器之前要经过下载器中间件
        request = self.downloader_middleware.prosess_request(request)
        # 把请求对象交给下载器，获取响应数据
        response = self.downloader.get_response(request)

        # 把响应交给爬虫之前要经过下载器中间件
        response = self.downloader_middleware.prosess_response(response)
        response = self.spider_middleware.prosess_response(response)

        # 让爬虫处理响应数据
        result = self.spider.parse(response)

        # 判断是数据还是请求对象
        if isinstance(result, Request):
            # 如果是请求对象则要经过爬虫中间件
            result = self.spider_middleware.prosess_request(result)
            self.scheduler.add_request(result)
        elif isinstance(result, Item):
            self.pipline.process_item(result)
        else:
            raise Exception('爬虫返回的数据必须是Itme和Request')


if __name__ == "__main__":
    engine = Engine()
    engine.start()
