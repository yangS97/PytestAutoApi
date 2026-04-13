#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/3/28 15:28
# @Author : 余少琪
# @Description: 缓存处理模块
#
# 【文件作用】
# 提供两种缓存机制：
# 1. Cache 类：基于文件的缓存（将数据写入 cache/ 目录下的文件）
# 2. CacheHandler 类：基于内存的缓存（使用 Python 字典 _cache_config）
#
# 【使用场景】
# - Cache 类：持久化存储用例数据池
# - CacheHandler：运行时数据共享（如登录 token、接口间传递的数据）
#
# 【Java 对比说明】
# - Cache 类类似于 Java 的基于文件的 Properties 配置存储
# - CacheHandler 类似于 Java 的 static ConcurrentHashMap 静态缓存
import os
from typing import Any, Text, Union
from common.setting import ensure_path_sep
from utils.other_tools.exceptions import ValueNotFoundError


class Cache:
    """
    文件缓存 —— 将数据写入文件系统持久化存储

    核心职责：
    - 设置缓存：将数据写入 cache/ 目录下的文件
    - 获取缓存：从文件中读取缓存数据
    - 清理缓存：删除缓存文件

    Java 类比：
    public class Cache {
        private String path;
        public void setCache(String key, Object value) { ... }
        public Object getCache() { ... }
        public void cleanCache() { ... }
    }
    """
    def __init__(self, filename: Union[Text, None]) -> None:
        """
        初始化缓存操作器

        Args:
            filename: 缓存文件名
                     - 不为 None：操作指定文件
                     - 为 None：操作整个 cache 目录
        """
        if filename:
            self.path = ensure_path_sep("\\cache" + filename)
        else:
            self.path = ensure_path_sep("\\cache")

    def set_cache(self, key: Text, value: Any) -> None:
        """
        设置单个键值对缓存

        只支持单字典类型缓存数据，如果文件已存在则覆盖之前的内容。

        Args:
            key: 缓存键名
            value: 缓存值

        示例：
        cache.set_cache("token", "abc123")
        # 文件内容：{"token": "abc123"}
        """
        with open(self.path, 'w', encoding='utf-8') as file:
            file.write(str({key: value}))

    def set_caches(self, value: Any) -> None:
        """
        设置多组缓存数据

        直接写入整个值（可以是任意 Python 对象转为字符串）。

        Args:
            value: 缓存内容（字典、列表等）

        示例：
        cache.set_caches({"token": "abc", "userId": 123})
        # 文件内容：{"token": "abc", "userId": 123}
        """
        with open(self.path, 'w', encoding='utf-8') as file:
            file.write(str(value))

    def get_cache(self) -> Any:
        """
        获取缓存数据

        Returns:
            str: 文件中的缓存内容（字符串格式）
            None: 如果文件不存在
        """
        try:
            with open(self.path, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            pass

    def clean_cache(self) -> None:
        """
        删除当前路径对应的缓存文件

        Raises:
            FileNotFoundError: 如果文件不存在
        """
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"您要删除的缓存文件不存在 {self.path}")
        os.remove(self.path)

    @classmethod
    def clean_all_cache(cls) -> None:
        """
        清除 cache/ 目录下的所有缓存文件
        """
        cache_path = ensure_path_sep("\\cache")

        # 列出目录下所有文件
        list_dir = os.listdir(cache_path)
        for i in list_dir:
            os.remove(cache_path + i)


# ==================== 内存缓存 ====================

# 全局内存缓存字典（类似于 Java 的 static Map）
# 这个字典在整个程序生命周期中持续存在
_cache_config = {}


class CacheHandler:
    """
    内存缓存处理器 —— 运行时数据共享

    使用全局字典 _cache_config 存储数据，适合：
    - 接口间传递数据（如 A 接口的 token 给 B 接口用）
    - 运行时临时数据存储
    - 性能敏感的场景（不需要文件 I/O）

    Java 类比：
    public class CacheHandler {
        private static final Map<String, Object> cacheConfig = new ConcurrentHashMap<>();

        public static Object getCache(String key) { ... }
        public static void updateCache(String cacheName, Object value) { ... }
    }

    使用示例：
    # 写入缓存
    CacheHandler.update_cache(cache_name="token", value="abc123")

    # 读取缓存
    token = CacheHandler.get_cache("token")
    """

    @staticmethod
    def get_cache(cache_data):
        """
        从内存缓存中获取数据

        Args:
            cache_data: 缓存键名

        Returns:
            缓存值

        Raises:
            ValueNotFoundError: 如果键不存在

        Java 类比：
        public static Object getCache(String key) {
            if (!cacheConfig.containsKey(key)) {
                throw new ValueNotFoundError(key + " not found");
            }
            return cacheConfig.get(key);
        }
        """
        try:
            return _cache_config[cache_data]
        except KeyError:
            raise ValueNotFoundError(f"{cache_data}的缓存数据未找到，请检查是否将该数据存入缓存中")

    @staticmethod
    def update_cache(*, cache_name, value):
        """
        将数据存入内存缓存

        Args:
            cache_name: 缓存键名
            value: 缓存值

        Java 类比：
        public static void updateCache(String cacheName, Object value) {
            cacheConfig.put(cacheName, value);
        }
        """
        _cache_config[cache_name] = value
