#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2022/5/23 18:27
# @Author  : 余少琪
# @Email   : 1603453211@qq.com
# @Description: 自定义异常类定义
#
# 【文件作用】
# 定义框架中使用的所有自定义异常。
# 所有异常都继承自 MyBaseFailure（基类异常）。
#
# 【Java 对比说明】
# 类似于 Java 中的自定义异常类：
# public class JsonpathExtractionFailed extends MyBaseFailure { ... }
#
# Python 的异常继承：
# MyBaseFailure
# ├── JsonpathExtractionFailed
# ├── NotFoundError
# │   ├── FileNotFound (也继承自 FileNotFoundError)
# │   └── SqlNotFound
# ├── DataAcquisitionFailed
# ├── ValueTypeError
# ├── SendMessageError
# └── ValueNotFoundError


class MyBaseFailure(Exception):
    """
    框架异常基类

    所有自定义异常都继承自这个类。
    类似于 Java 中的：public class MyBaseFailure extends Exception { }
    """
    pass


class JsonpathExtractionFailed(MyBaseFailure):
    """
    JSONPath 提取失败异常

    当通过 JSONPath 从 JSON 数据中提取字段时，
    如果路径不正确或数据中不存在该字段，则抛出此异常。

    使用场景：
    - 断言引擎中 JSONPath 提取响应字段失败
    - 依赖处理器中 JSONPath 提取接口数据失败
    """
    pass


class NotFoundError(MyBaseFailure):
    """
    资源未找到异常基类

    通用的资源不存在异常，子类包括 FileNotFound 和 SqlNotFound。
    """
    pass


class FileNotFound(FileNotFoundError, NotFoundError):
    """
    文件未找到异常

    同时继承 Python 内置的 FileNotFoundError 和自定义的 NotFoundError，
    可以捕获为两种异常类型中的任意一种。

    使用场景：
    - YAML 用例文件路径不存在
    - 缓存文件不存在
    """
    pass


class SqlNotFound(NotFoundError):
    """
    SQL 查询未找到数据异常

    使用场景：
    - 定义了 SQL 断言，但没有填写 SQL 语句
    - SQL 查询返回空结果
    """
    pass


class AssertTypeError(MyBaseFailure):
    """
    断言类型错误异常

    使用场景：
    - YAML 中定义的 AssertType 不是 "SQL" 或 None
    - 不支持的断言类型
    """
    pass


class DataAcquisitionFailed(MyBaseFailure):
    """
    数据获取失败异常

    使用场景：
    - 前置 SQL 查询失败（无结果返回）
    - 断言 SQL 查询失败
    """
    pass


class ValueTypeError(MyBaseFailure):
    """
    数据类型错误异常

    使用场景：
    - SQL 断言中传入的不是 list 类型
    - 其他类型校验失败
    """
    pass


class SendMessageError(MyBaseFailure):
    """
    消息发送失败异常

    使用场景：
    - 通知发送失败（钉钉/企业微信/邮件/飞书）
    """
    pass


class ValueNotFoundError(MyBaseFailure):
    """
    值未找到异常（最常用的自定义异常）

    使用场景：
    - 缓存中找不到对应的键
    - YAML 用例中缺少必要参数
    - JSONPath 提取失败
    """
    pass
