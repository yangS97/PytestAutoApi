#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/3/28 15:26
# @Author : 余少琪
# @Description: 文件路径扫描工具
#
# 【文件作用】
# 递归扫描指定目录下的所有文件路径。
# 主要用于：
# 1. 扫描 data/ 目录下所有的 YAML 测试用例文件
# 2. 扫描 Allure 报告目录下所有测试用例的 JSON 数据
#
# 【Java 对比说明】
# 类似于 Java 的 Files.walk() 或 FileUtils.listFiles()：
# List<Path> files = Files.walk(Paths.get(dirPath))
#     .filter(Files::isRegularFile)
#     .filter(p -> p.toString().endsWith(".yaml"))
#     .collect(Collectors.toList());

import os


def get_all_files(file_path, yaml_data_switch=False) -> list:
    """
    递归获取目录下所有文件的路径

    【执行流程】
    1. 使用 os.walk() 递归遍历目录树
    2. 收集所有文件路径
    3. 如果 yaml_data_switch=True，则只返回 .yaml/.yml 文件

    Args:
        file_path: 要扫描的目录路径
        yaml_data_switch: 是否只返回 YAML 格式文件
                          - True: 只返回 .yaml 和 .yml 文件
                          - False: 返回所有文件

    Returns:
        list: 文件路径列表

    Java 类比：
    public static List<String> getAllFiles(String dirPath, boolean yamlOnly) {
        List<String> files = new ArrayList<>();
        Files.walk(Paths.get(dirPath))
            .filter(Files::isRegularFile)
            .filter(p -> !yamlOnly || p.toString().endsWith(".yaml"))
            .forEach(p -> files.add(p.toString()));
        return files;
    }
    """
    filename = []
    # os.walk 递归遍历目录树
    # root: 当前目录路径
    # dirs: 当前目录下的子目录列表
    # files: 当前目录下的文件列表
    for root, dirs, files in os.walk(file_path):
        for _file_path in files:
            path = os.path.join(root, _file_path)
            if yaml_data_switch:
                # 只保留 YAML 格式文件
                if 'yaml' in path or '.yml' in path:
                    filename.append(path)
            else:
                # 返回所有文件
                filename.append(path)
    return filename
