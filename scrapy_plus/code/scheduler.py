# _*_coding:utf-8_*_
# 兼容python2和python3
from six.moves.queue import Queue

"""
缓存请求对象
请求去重
"""


class Scheduler(object):

    def __init__(self):
        self.queue = Queue()

    def add_request(self, request):

        self.queue.put(request)

    def get_request(self):
        
        return self.queue.get()

    def senn_request(self):
        # 请求对象去重
        pass