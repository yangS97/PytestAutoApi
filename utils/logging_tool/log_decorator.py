#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/3/28 15:28
# @Author : 余少琪
# @Description: 日志装饰器 —— 控制日志输出开关
#
# 【文件作用】
# 提供一个装饰器函数，用于控制被装饰函数的日志输出。
# 默认情况下，在 http_request 方法上使用此装饰器，
# 每次请求完成后，自动将请求/响应信息打印到日志中。
#
# 【Java 对比说明】
# - 装饰器（decorator）类似于 Java 的 AOP（面向切面编程）
# - @wraps 类似于 Java 的反射保留原方法信息
# - 类似于在方法前后添加日志记录的 Interceptor
import ast
from functools import wraps
from utils.read_files_tools.regular_control import cache_regular
from utils.logging_tool.log_control import INFO, ERROR


def log_decorator(switch: bool):
    """
    日志装饰器 —— 在函数执行后打印请求/响应信息

    【装饰器原理】
    这是一个带参数的装饰器，返回一个装饰器函数。
    装饰器的嵌套结构：
    1. log_decorator(switch) —— 接收开关参数
    2. decorator(func) —— 接收被装饰的函数
    3. swapper(*args, **kwargs) —— 替换原函数的包装函数

    Args:
        switch: 日志开关（True=开启，False=关闭）

    Returns:
        装饰器函数

    Java 类比：
    @Aspect
    public class LogAspect {
        @Around("execution(* RequestControl.httpRequest(..))")
        public Object logRequest(ProceedingJoinPoint pjp) throws Throwable {
            Object res = pjp.proceed();
            if (switch) {
                log.info("Request details...");
            }
            return res;
        }
    }

    使用示例：
    @log_decorator(True)
    def http_request(self):
        # 发送 HTTP 请求
        return response_data
    """
    def decorator(func):
        @wraps(func)  # 保留原函数的元数据（名称、文档字符串等）
        def swapper(*args, **kwargs):
            # 执行原函数
            res = func(*args, **kwargs)

            # 判断日志为开启状态，才打印日志
            if switch:
                _log_msg = f"\n======================================================\n" \
                           f"用例标题: {res.detail}\n" \
                           f"请求路径: {res.url}\n" \
                           f"请求方式: {res.method}\n" \
                           f"请求头:   {res.headers}\n" \
                           f"请求内容: {res.request_body}\n" \
                           f"接口响应内容: {res.response_data}\n" \
                           f"接口响应时长: {res.res_time} ms\n" \
                           f"Http状态码: {res.status_code}\n" \
                           "====================================================="

                # 解析 is_run 字段
                _is_run = ast.literal_eval(cache_regular(str(res.is_run)))

                # 判断正常执行的用例，控制台输出绿色日志
                if _is_run in (True, None) and res.status_code == 200:
                    INFO.logger.info(_log_msg)
                else:
                    # 失败的用例，控制台打印红色日志
                    ERROR.logger.error(_log_msg)

            return res
        return swapper
    return decorator
