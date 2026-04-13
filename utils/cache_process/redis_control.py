#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/3/28 15:28
# @Author : 余少琪
# @Description: Redis 缓存操作封装
#
# 【文件作用】
# 封装 Redis 的基本操作，支持：
# - 字符串存取（支持过期时间、条件设置）
# - 批量存取
# - 键值判断
# - 自增操作（处理并发问题）
# - 删除操作
#
# 【Java 对比说明】
# 类似于 Java 中使用 Jedis/RedisTemplate 操作 Redis：
# @Repository
# public class RedisHandler {
#     @Autowired
#     private RedisTemplate<String, Object> redisTemplate;
#
#     public void setString(String name, Object value, long expTime) { ... }
#     public Object get(String name) { ... }
#     public void incr(String key) { ... }
# }
from typing import Text, Any
import redis


class RedisHandler:
    """
    Redis 缓存操作封装

    核心职责：
    - 字符串的单个/批量存取
    - 键值存在判断
    - 原子自增
    - 清理操作

    Java 类比：
    public class RedisHandler {
        private RedisClient redis;

        public RedisHandler() {
            this.redis = new RedisClient("127.0.0.0", 6379);
        }

        public void setString(String name, Object value, long expTime) { ... }
        public Object get(String name) { ... }
        public boolean keyExists(String key) { ... }
        public void incr(String key) { ... }
    }
    """

    def __init__(self):
        """
        初始化 Redis 连接

        注意：此处的连接信息是硬编码的，实际使用应该从配置文件读取。
        """
        self.host = '127.0.0.0'
        self.port = 6379
        self.database = 0
        self.password = 123456
        self.charset = 'UTF-8'
        # 创建 Redis 客户端
        # decode_responses=True 表示返回的数据自动解码为字符串
        self.redis = redis.Redis(
            self.host,
            port=self.port,
            password=self.password,
            decode_responses=True,
            db=self.database
        )

    def set_string(self, name: Text, value, exp_time=None, exp_milliseconds=None,
                   name_not_exist=False, name_exit=False) -> None:
        """
        缓存中写入字符串（单个）

        Args:
            name: 缓存键名
            value: 缓存值
            exp_time: 过期时间（秒）
            exp_milliseconds: 过期时间（毫秒）
            name_not_exist: 如果为 True，则只有键不存在时才执行 set（新增）
            name_exit: 如果为 True，则只有键存在时才执行 set（修改）
        """
        self.redis.set(
            name,
            value,
            ex=exp_time,
            px=exp_milliseconds,
            nx=name_not_exist,
            xx=name_exit
        )

    def key_exit(self, key: Text):
        """
        判断 Redis 中的键是否存在

        Args:
            key: 键名

        Returns:
            bool: 存在返回 True，不存在返回 False
        """
        return self.redis.exists(key)

    def incr(self, key: Text):
        """
        使用 Redis 的原子自增方法

        当 key 不存在时，先初始化为 0，然后每次调用 +1。
        这个方法是原子操作，适合处理并发问题（如计数器）。

        Args:
            key: 键名

        Returns:
            int: 自增后的值
        """
        return self.redis.incr(key)

    def get_key(self, name: Any) -> Text:
        """
        读取缓存

        Args:
            name: 缓存键名

        Returns:
            str: 缓存值；键不存在时返回 None
        """
        return self.redis.get(name)

    def set_many(self, *args, **kwargs):
        """
        批量设置缓存

        支持两种方式：
        1. 字典方式：set_many({'k1': 'v1', 'k2': 'v2'})
        2. 关键字参数：set_many(k1="v1", k2="v2")
        """
        self.redis.mset(*args, **kwargs)

    def get_many(self, *args):
        """
        批量获取多个值

        Args:
            *args: 多个键名

        Returns:
            list: 对应的值列表
        """
        results = self.redis.mget(*args)
        return results

    def del_all_cache(self):
        """
        清理所有缓存

        遍历所有键并删除。
        """
        for key in self.redis.keys():
            self.del_cache(key)

    def del_cache(self, name):
        """
        删除指定缓存

        Args:
            name: 缓存键名
        """
        self.redis.delete(name)
