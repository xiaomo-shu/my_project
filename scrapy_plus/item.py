#_*_coding:utf-8_*_
"""
封装爬虫提取出来的数据
_将来可以根据类型来判断提取的是数据还是请求
"""


class Item(object):
    
    def __init__(self, data)
    # 设置为私有属性，保护Item中的数据不被篡改
    self._data = data 

    @property
    def data(self)
    return self._data
