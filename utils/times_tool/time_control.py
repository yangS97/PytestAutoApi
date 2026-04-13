#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/3/28 15:47
# @Author : 余少琪
# @Description: 时间处理工具
#
# 【文件作用】
# 提供各种时间格式转换和获取当前时间的函数。
# 支持的操作：
# - 计算时间差（毫秒）
# - 日期格式 -> 时间戳
# - 时间戳 -> 日期格式
# - 获取当前时间（字符串格式）
# - 获取当前时间戳
# - 获取几分钟后的时间戳
#
# 【Java 对比说明】
# 类似于 Java 中的 SimpleDateFormat / Instant / LocalDateTime 工具类：
# public class TimeUtils {
#     public static long toTimestamp(String dateStr) { ... }
#     public static String toDateStr(long timestamp) { ... }
#     public static long nowMillis() { ... }
# }

import time
from typing import Text
from datetime import datetime


def count_milliseconds():
    """
    计算两个时间点之间的毫秒差

    注意：这个方法目前实现有问题，access_start 和 access_end
    几乎同时获取，差值永远接近 0。

    Returns:
        int: 毫秒差
    """
    access_start = datetime.now()
    access_end = datetime.now()
    access_delta = (access_end - access_start).seconds * 1000
    return access_delta


def timestamp_conversion(time_str: Text) -> int:
    """
    时间戳转换 —— 将日期字符串转为时间戳（毫秒）

    Args:
        time_str: 日期字符串，格式为 "%Y-%m-%d %H:%M:%S"
                  如 "2022-03-28 14:30:00"

    Returns:
        int: 时间戳（毫秒）

    Raises:
        ValueError: 如果日期格式不正确

    Java 类比：
    public static long toTimestamp(String timeStr) {
        SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        Date date = sdf.parse(timeStr);
        return date.getTime();
    }
    """
    try:
        datetime_format = datetime.strptime(str(time_str), "%Y-%m-%d %H:%M:%S")
        timestamp = int(
            time.mktime(datetime_format.timetuple()) * 1000.0
            + datetime_format.microsecond / 1000.0
        )
        return timestamp
    except ValueError as exc:
        raise ValueError('日期格式错误, 需要传入得格式为 "%Y-%m-%d %H:%M:%S" ') from exc


def time_conversion(time_num: int):
    """
    时间戳转日期 —— 将时间戳转为日期字符串

    Args:
        time_num: 时间戳（毫秒）

    Returns:
        str: 日期字符串，格式为 "%Y-%m-%d %H:%M:%S"

    Java 类比：
    public static String toDateStr(long timestamp) {
        Date date = new Date(timestamp);
        return new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(date);
    }
    """
    if isinstance(time_num, int):
        # 毫秒转为秒
        time_stamp = float(time_num / 1000)
        time_array = time.localtime(time_stamp)
        other_style_time = time.strftime("%Y-%m-%d %H:%M:%S", time_array)
        return other_style_time


def now_time():
    """
    获取当前时间

    Returns:
        str: 当前时间，格式为 "2021-12-11 12:39:25"

    Java 类比：
    public static String nowTime() {
        return new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new Date());
    }
    """
    localtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    return localtime


def now_time_day():
    """
    获取当前日期（不含时间）

    Returns:
        str: 当前日期，格式为 "2021-12-11"

    Java 类比：
    public static String nowTimeDay() {
        return new SimpleDateFormat("yyyy-MM-dd").format(new Date());
    }
    """
    localtime = time.strftime("%Y-%m-%d", time.localtime())
    return localtime


def get_time_for_min(minute: int) -> int:
    """
    获取 N 分钟后的时间戳

    Args:
        minute: 分钟数

    Returns:
        int: N 分钟后的时间戳（毫秒）

    Java 类比：
    public static long getFutureTimestamp(int minutes) {
        return System.currentTimeMillis() + minutes * 60 * 1000;
    }
    """
    return int(time.time() + 60 * minute) * 1000


def get_now_time() -> int:
    """
    获取当前时间戳（整数，毫秒）

    Returns:
        int: 当前时间戳（毫秒）

    Java 类比：
    public static long nowMillis() {
        return System.currentTimeMillis();
    }
    """
    return int(time.time()) * 1000
