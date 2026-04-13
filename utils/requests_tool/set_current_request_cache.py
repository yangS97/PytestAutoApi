#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2022/6/2 11:30
# @Author  : 余少琪
# @Description: 当前请求缓存设置
#
# 【文件作用】
# 在 HTTP 请求执行完毕后，根据 YAML 中 current_request_set_cache
# 的定义，将请求或响应中的数据提取出来并写入缓存。
#
# 【使用场景】
# 在 YAML 用例中，可以定义当前请求的哪些数据需要存入缓存：
# current_request_set_cache:
#   - type: "response"          # 从响应中提取
#     jsonpath: "$.data.userId" # JSONPath 表达式
#     name: "userId"            # 缓存键名
#   - type: "request"           # 从请求中提取
#     jsonpath: "$.data.name"
#     name: "userName"
#
# 【Java 对比说明】
# 类似于在拦截器的 postHandle 方法中提取响应数据并放入缓存：
# public void postHandle(ResponseData response) {
#     for (CacheConfig config : currentRequestSetCache) {
#         if ("response".equals(config.getType())) {
#             Object value = JsonPath.read(response.getBody(), config.getJsonpath());
#             cache.put(config.getName(), value);
#         }
#     }
# }
import json
from typing import Text
from jsonpath import jsonpath
from utils.other_tools.exceptions import ValueNotFoundError
from utils.cache_process.cache_control import CacheHandler


class SetCurrentRequestCache:
    """
    当前请求缓存设置器

    核心职责：
    - 从当前请求的参数中提取数据并缓存
    - 从当前响应的结果中提取数据并缓存

    Java 类比：
    public class SetCurrentRequestCache {
        private List<CurrentRequestSetCache> cacheConfigs;
        private Map<String, Object> requestData;
        private String responseData;

        public void setCachesMain() {
            for (CurrentRequestSetCache config : cacheConfigs) {
                if ("request".equals(config.getType())) {
                    setRequestCache(config.getJsonpath(), config.getName());
                } else if ("response".equals(config.getType())) {
                    setResponseCache(config.getJsonpath(), config.getName());
                }
            }
        }
    }
    """

    def __init__(self, current_request_set_cache, request_data, response_data):
        """
        初始化缓存设置器

        Args:
            current_request_set_cache: 缓存配置列表（来自 YAML）
            request_data: 请求参数（字典）
            response_data: HTTP 响应对象
        """
        self.current_request_set_cache = current_request_set_cache
        # 将请求数据包装为 {data: ...} 格式，方便 JSONPath 提取
        self.request_data = {"data": request_data}
        # 响应数据转为字符串（JSON 格式）
        self.response_data = response_data.text

    def set_request_cache(self, jsonpath_value: Text, cache_name: Text) -> None:
        """
        从请求参数中提取数据并缓存

        Args:
            jsonpath_value: JSONPath 表达式（如 "$.data.userId"）
            cache_name: 缓存键名（如 "userId"）

        Raises:
            ValueNotFoundError: 如果 JSONPath 提取失败
        """
        _request_data = jsonpath(self.request_data, jsonpath_value)
        if _request_data is not False:
            # 提取成功，写入缓存
            CacheHandler.update_cache(cache_name=cache_name, value=_request_data[0])
        else:
            raise ValueNotFoundError(
                "缓存设置失败，程序中未检测到需要缓存的数据。"
                f"请求参数: {self.request_data}"
                f"提取的 jsonpath 内容: {jsonpath_value}"
            )

    def set_response_cache(self, jsonpath_value: Text, cache_name) -> None:
        """
        从响应结果中提取数据并缓存

        Args:
            jsonpath_value: JSONPath 表达式（如 "$.data.token"）
            cache_name: 缓存键名（如 "token"）

        Raises:
            ValueNotFoundError: 如果 JSONPath 提取失败
        """
        _response_data = jsonpath(json.loads(self.response_data), jsonpath_value)
        if _response_data is not False:
            # 提取成功，写入缓存
            CacheHandler.update_cache(cache_name=cache_name, value=_response_data[0])
        else:
            raise ValueNotFoundError(
                "缓存设置失败，程序中未检测到需要缓存的数据。"
                f"请求参数: {self.response_data}"
                f"提取的 jsonpath 内容: {jsonpath_value}"
            )

    def set_caches_main(self) -> None:
        """
        缓存设置主入口

        遍历所有缓存配置，根据类型（request/response）分发到对应的处理方法。

        【执行流程】
        1. 检查是否定义了缓存配置
        2. 遍历每个缓存配置
        3. 根据 type 字段分发：
           - "request" -> 从请求参数中提取
           - "response" -> 从响应结果中提取
        """
        if self.current_request_set_cache is not None:
            for i in self.current_request_set_cache:
                _jsonpath = i.jsonpath
                _cache_name = i.name
                if i.type == 'request':
                    self.set_request_cache(jsonpath_value=_jsonpath, cache_name=_cache_name)
                elif i.type == 'response':
                    self.set_response_cache(jsonpath_value=_jsonpath, cache_name=_cache_name)
