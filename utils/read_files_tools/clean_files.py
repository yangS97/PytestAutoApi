#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/4/7 11:56
# @Author : 余少琪
# @Description: 文件清理工具
#
# 【文件作用】
# 递归删除指定目录下的所有文件。
# 主要用于每次测试运行前清理旧的报告目录。
#
# 【Java 对比说明】
# 类似于 Java 的 FileUtils.deleteDirectory() 或递归删除：
# public static void deleteDirectory(File dir) {
#     for (File file : dir.listFiles()) {
#         if (file.isDirectory()) {
#             deleteDirectory(file);
#         } else {
#             file.delete();
#         }
#     }
# }

import os


def del_file(path):
    """
    递归删除目录下的所有文件

    注意：
    - 这个方法只删除文件，不删除目录本身
    - 目录结构会保留，只是里面的文件被清空

    Args:
        path: 需要清理的目录路径

    执行流程：
    1. 列出目录下的所有子项
    2. 如果是子目录，递归调用 del_file
    3. 如果是文件，直接删除

    Java 类比：
    public static void delFiles(String path) {
        File dir = new File(path);
        for (File file : dir.listFiles()) {
            if (file.isDirectory()) {
                delFiles(file.getPath());
            } else {
                file.delete();
            }
        }
    }
    """
    list_path = os.listdir(path)
    for i in list_path:
        c_path = os.path.join(path, i)
        if os.path.isdir(c_path):
            # 递归处理子目录
            del_file(c_path)
        else:
            # 删除文件
            os.remove(c_path)
