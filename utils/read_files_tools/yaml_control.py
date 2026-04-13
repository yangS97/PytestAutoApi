#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/3/28 10:51
# @Author : 余少琪
# @Description: YAML 文件读写封装
#
# 【文件作用】
# 封装 YAML 文件的读取和写入操作，提供统一的接口供框架其他模块调用。
#
# 【Java 对比说明】
# - yaml.load 类似于 Java 的 new ObjectMapper(new YAMLFactory()).readValue(yaml, Map.class)
# - open(file, 'r', encoding='utf-8') 类似于 Java 的 new BufferedReader(new InputStreamReader(...))

import os
import ast
import yaml.scanner
from utils.read_files_tools.regular_control import regular


class GetYamlData:
    """
    YAML 文件数据读取器

    Java 类比：
    public class GetYamlData {
        private String filePath;
        public Map<String, Object> getYamlData() { ... }
        public int writeYamlData(String key, Object value) { ... }
    }
    """

    def __init__(self, file_dir):
        """
        初始化 YAML 数据读取器

        Args:
            file_dir: YAML 文件的绝对路径
        """
        self.file_dir = str(file_dir)

    def get_yaml_data(self) -> dict:
        """
        读取 YAML 文件并解析为 Python 字典

        Returns:
            dict: YAML 文件内容解析后的字典

        Raises:
            FileNotFoundError: 如果文件路径不存在

        Java 类比：
        public Map<String, Object> getYamlData() throws IOException {
            try (InputStream is = new FileInputStream(filePath)) {
                return new Yaml().load(is);
            }
        }
        """
        # 判断文件是否存在
        if os.path.exists(self.file_dir):
            data = open(self.file_dir, 'r', encoding='utf-8')
            # yaml.load 将 YAML 文件内容解析为 Python 字典
            # Loader=yaml.FullLoader 是安全的加载器，不执行任意代码
            res = yaml.load(data, Loader=yaml.FullLoader)
        else:
            raise FileNotFoundError("文件路径不存在")
        return res

    def write_yaml_data(self, key: str, value) -> int:
        """
        修改 YAML 文件中指定 key 的值，并保留原有注释

        实现方式：
        逐行读取文件，找到匹配的 key 行，替换其值。
        这种方式可以保留 YAML 文件中的注释内容。

        Args:
            key: 需要修改的键名
            value: 新的值

        Returns:
            int: 1 表示修改成功，0 表示未找到匹配的 key

        Java 类比：
        public int writeYamlData(String key, Object value) throws IOException {
            // 逐行读取，找到匹配的 key，替换值
            // 类似于 Properties.setProperty() 但保留注释
        }
        """
        with open(self.file_dir, 'r', encoding='utf-8') as file:
            # 读取所有非空行
            lines = []
            for line in file.readlines():
                if line != '\n':
                    lines.append(line)
            file.close()

        with open(self.file_dir, 'w', encoding='utf-8') as file:
            flag = 0
            for line in lines:
                left_str = line.split(":")[0]  # 提取冒号前的键名
                if key == left_str and '#' not in line:  # 排除注释行
                    newline = f"{left_str}: {value}"
                    line = newline
                    file.write(f'{line}\n')
                    flag = 1
                else:
                    file.write(f'{line}')
            file.close()
            return flag


class GetCaseData(GetYamlData):
    """
    测试用例数据读取器

    继承 GetYamlData，增加了用例数据格式兼容和动态表达式解析的功能。

    Java 类比：
    public class GetCaseData extends GetYamlData { ... }
    """

    def get_different_formats_yaml_data(self) -> list:
        """
        获取 YAML 数据并转为列表格式

        兼容不同格式的 YAML 文件，将字典的键转为列表。

        Returns:
            list: YAML 文件的所有键名列表
        """
        res_list = []
        for i in self.get_yaml_data():
            res_list.append(i)
        return res_list

    def get_yaml_case_data(self):
        """
        获取测试用例数据，并进行动态表达式解析

        执行流程：
        1. 读取 YAML 文件数据
        2. 将字典转为字符串
        3. 通过 regular() 解析动态表达式（如 ${{random_int()}}）
        4. 将处理后的字符串转为 Python 字典

        Returns:
            dict: 解析动态表达式后的用例数据
        """
        _yaml_data = self.get_yaml_data()
        # 正则处理 YAML 文件中的动态表达式
        re_data = regular(str(_yaml_data))
        return ast.literal_eval(re_data)
