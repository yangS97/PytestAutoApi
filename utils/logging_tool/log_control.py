#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/3/28 15:21
# @Author : 余少琪
# @Description: 日志工具 —— 带颜色输出的日志管理器
#
# 【文件作用】
# 封装 Python 的 logging 模块，提供：
# 1. 带颜色区分的控制台输出（DEBUG=青色, INFO=绿色, WARNING=黄色, ERROR=红色）
# 2. 按日期自动分割的日志文件（每天一个文件）
# 3. 全局日志单例（INFO, ERROR, WARNING）
#
# 【Java 对比说明】
# - 类似于 Java 的 Logback/Log4j2 配置
# - colorlog 类似于 Java 中的 ANSI 颜色输出
# - TimedRotatingFileHandler 类似于 Java 的 DailyRollingFileAppender
import logging
from logging import handlers
from typing import Text
import colorlog
import time
from common.setting import ensure_path_sep


class LogHandler:
    """
    日志处理器 —— 配置不同等级的日志输出

    每个 LogHandler 实例包含：
    - 一个 Logger 对象
    - 一个控制台 Handler（带颜色输出）
    - 一个文件 Handler（按日期分割）

    Java 类比：
    public class LogHandler {
        private Logger logger;
        private static Map<String, Level> levelRelations;

        public LogHandler(String filename, String level, String when, String fmt) {
            this.logger = Logger.getLogger(filename);
            // 配置控制台和文件输出
        }
    }
    """
    # 日志级别关系映射（Python logging 模块的级别常量）
    level_relations = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }

    def __init__(
            self,
            filename: Text,
            level: Text = "info",
            when: Text = "D",
            fmt: Text = "%(levelname)-8s%(asctime)s%(name)s:%(filename)s:%(lineno)d %(message)s"
    ):
        """
        初始化日志处理器

        Args:
            filename: 日志文件路径
            level: 日志级别（debug/info/warning/error/critical）
            when: 日志文件分割周期（D=按天，H=按小时，M=按分钟）
            fmt: 日志格式（用于文件输出）
        """
        self.logger = logging.getLogger(filename)

        # 获取带颜色的格式化器（用于控制台输出）
        formatter = self.log_color()

        # 设置日志格式（用于文件输出）
        format_str = logging.Formatter(fmt)
        # 设置日志级别
        self.logger.setLevel(self.level_relations.get(level))
        # 往屏幕上输出（控制台 Handler）
        screen_output = logging.StreamHandler()
        # 设置屏幕上显示的格式（带颜色）
        screen_output.setFormatter(formatter)
        # 往文件里写入（按时间分割的 Handler）
        # backupCount=3 表示保留最近 3 个日志文件
        time_rotating = handlers.TimedRotatingFileHandler(
            filename=filename,
            when=when,
            backupCount=3,
            encoding='utf-8'
        )
        # 设置文件里写入的格式（不带颜色）
        time_rotating.setFormatter(format_str)
        # 把 Handler 加到 Logger 里
        self.logger.addHandler(screen_output)
        self.logger.addHandler(time_rotating)
        self.log_path = ensure_path_sep('\\logs\\log.log')

    @classmethod
    def log_color(cls):
        """
        创建带颜色的日志格式化器

        颜色配置：
        - DEBUG: 青色（调试信息，不太重要）
        - INFO: 绿色（正常信息）
        - WARNING: 黄色（警告，需要关注）
        - ERROR: 红色（错误，需要处理）
        - CRITICAL: 红色（严重错误）

        Returns:
            ColoredFormatter: 带颜色的格式化器
        """
        log_colors_config = {
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red',
        }

        formatter = colorlog.ColoredFormatter(
            '%(log_color)s[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s',
            log_colors=log_colors_config
        )
        return formatter


# ==================== 全局日志单例 ====================

# 获取当前日期（用于日志文件命名）
now_time_day = time.strftime("%Y-%m-%d", time.localtime())

# INFO 日志处理器：记录 info 级别及以上的日志
# 文件路径：logs/info-YYYY-MM-DD.log
INFO = LogHandler(ensure_path_sep(f"\\logs\\info-{now_time_day}.log"), level='info')

# ERROR 日志处理器：只记录 error 级别及以上的日志
# 文件路径：logs/error-YYYY-MM-DD.log
ERROR = LogHandler(ensure_path_sep(f"\\logs\\error-{now_time_day}.log"), level='error')

# WARNING 日志处理器：记录 warning 级别及以上的日志
# 文件路径：logs/warning-YYYY-MM-DD.log
WARNING = LogHandler(ensure_path_sep(f'\\logs\\warning-{now_time_day}.log'))

if __name__ == '__main__':
    ERROR.logger.error("测试")
