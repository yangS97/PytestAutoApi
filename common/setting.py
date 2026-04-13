#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2021/11/25 13:07
# @Author : 余少琪
# @Description: 路径配置工具模块
#
# 提供获取项目根路径和跨平台路径转换的功能
#
# 【Java 对比说明】
# - os.path 类似于 Java 中的 java.nio.file.Paths / java.io.File
# - os.sep 类似于 Java 中的 File.separator
# - __file__ 类似于 Java 中的 getClass().getResource("") 获取当前文件路径

import os
from typing import Text


def root_path():
    """
    获取项目根路径

    原理：
    - __file__ 是当前文件的绝对路径（setting.py 本身）
    - os.path.dirname() 获取所在目录
    - 调用两次 dirname 是因为 setting.py 在 common/ 目录下
    - common/ 的上一级就是项目根目录

    目录结构示意：
    PytestAutoApi/          <- 这就是我们要的根路径
    └── common/
        └── setting.py      <- __file__ 指向这里

    Returns:
        str: 项目根目录的绝对路径

    Java 类比：
    new File(getClass().getResource("/../../").getFile()).getAbsolutePath()
    """
    path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return path


def ensure_path_sep(path: Text) -> Text:
    """
    兼容 Windows 和 Linux 不同操作系统的路径分隔符

    问题背景：
    - Windows 使用反斜杠 \\ 作为路径分隔符（如 C:\\Users\\test）
    - Linux/Mac 使用正斜杠 / 作为路径分隔符（如 /home/test）
    - 如果代码中硬编码了某一种分隔符，在另一个系统上可能无法正常工作

    解决方式：
    将路径中的 / 或 \\ 统一替换为当前系统的 os.sep，
    然后拼接到项目根路径后面

    Args:
        path: 相对路径（如 "\\common\\config.yaml" 或 "/common/config.yaml"）

    Returns:
        str: 拼接后的完整绝对路径（已适配当前系统分隔符）

    Java 类比：
    Paths.get(rootPath, path.replace('/', File.separatorChar).replace('\\', File.separatorChar)).toString()

    使用示例：
    >>> ensure_path_sep("\\common\\config.yaml")  # Windows 写法
    '/Users/ys/PyCharmProject/PytestAutoApi/common/config.yaml'
    >>> ensure_path_sep("/common/config.yaml")        # Linux 写法
    '/Users/ys/PyCharmProject/PytestAutoApi/common/config.yaml'
    """
    # 如果路径中使用的是 /，则替换为当前系统的 os.sep
    if "/" in path:
        path = os.sep.join(path.split("/"))

    # 如果路径中使用的是 \\，则替换为当前系统的 os.sep
    if "\\" in path:
        path = os.sep.join(path.split("\\"))

    # 将处理后的相对路径拼接到项目根路径上
    return root_path() + path
