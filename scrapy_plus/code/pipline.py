#  _*_codeing:utf-8_*_
"""
管道模块：
 处理数据
"""


class Pipeline(object):

    def process_item(self, item):
        # 处理爬虫提取出来的数据

        print(item.data)

        return item