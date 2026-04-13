#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/3/29 14:43
# @Author : 余少琪
# @Description: 响应耗时监控装饰器
#
# 【文件作用】
# 统计被装饰函数的执行时间（接口响应时长），
# 如果超过设定的阈值，则在控制台打印红色告警日志。
#
# 【使用场景】
# 在 http_request 方法上使用 @execution_duration(3000)，
# 当接口响应时间超过 3000ms 时，输出告警日志。
#
# 【Java 对比说明】
# 类似于 Java 中的性能监控切面：
# @Aspect
# public class PerformanceAspect {
#     @Around("execution(* RequestControl.httpRequest(..))")
#     public Object monitorPerformance(ProceedingJoinPoint pjp) {
#         long start = System.currentTimeMillis();
#         Object res = pjp.proceed();
#         long elapsed = System.currentTimeMillis() - start;
#         if (elapsed > threshold) {
#             log.error("Performance warning: {}ms", elapsed);
#         }
#         return res;
#     }
# }
from utils.logging_tool.log_control import ERROR


def execution_duration(number: int):
    """
    函数执行时间监控装饰器

    监控被装饰函数的执行耗时，如果超过阈值则输出 ERROR 级别的告警日志。

    Args:
        number: 函数预计运行时长阈值（毫秒）
               默认 3000ms

    Returns:
        装饰器函数

    使用示例：
    @execution_duration(3000)
    def http_request(self):
        # 发送 HTTP 请求
        return response_data  # response_data.res_time 是响应时长（ms）
    """
    def decorator(func):
        def swapper(*args, **kwargs):
            # 执行原函数
            res = func(*args, **kwargs)
            # 获取响应时长（毫秒）
            run_time = res.res_time
            # 如果时间超过阈值，则打印告警日志
            if run_time > number:
                ERROR.logger.error(
                    "\n==============================================\n"
                    "测试用例执行时间较长，请关注.\n"
                    "函数运行时间: %s ms\n"
                    "测试用例相关数据: %s\n"
                    "=================================================",
                    run_time, res
                )
            return res
        return swapper
    return decorator
