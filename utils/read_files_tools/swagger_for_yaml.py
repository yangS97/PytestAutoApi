#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/8/11 10:51
# @Author : 余少琪
# @Description: Swagger OpenAPI 转 YAML 用例生成器
#
# 【文件作用】
# 从 Swagger 的 OpenAPI JSON 文件自动生成 YAML 测试用例模板。
# 这样开发者可以直接从 API 文档生成测试用例，而不需要手动编写 YAML。
#
# 【工作流程】
# 1. 读取 ./file/test_OpenAPI.json 文件（Swagger 导出的 OpenAPI 数据）
# 2. 遍历所有 API 路径和方法
# 3. 为每个 API 生成一个 YAML 用例模板
# 4. 写入 data/ 目录（按 API 路径分层）
#
# 【使用方式】
# 1. 从 Swagger UI 导出 OpenAPI JSON
# 2. 保存到 ./file/test_OpenAPI.json
# 3. 运行此脚本：python swagger_for_yaml.py
#
# 【Java 对比说明】
# 类似于 Java 中通过 Swagger Codegen 从 OpenAPI 生成客户端代码的过程，
# 但这里生成的是 YAML 测试用例而非 Java 代码。
import json
from jsonpath import jsonpath
from common.setting import ensure_path_sep
from typing import Dict
from ruamel import yaml
import os


class SwaggerForYaml:
    """
    Swagger OpenAPI JSON 转 YAML 测试用例

    核心职责：
    - 解析 Swagger JSON 数据
    - 提取 API 信息（路径、方法、参数、请求头等）
    - 生成符合框架规范的 YAML 用例

    Java 类比：
    public class SwaggerForYaml {
        private Map<String, Object> swaggerData;

        public SwaggerForYaml() {
            this.swaggerData = loadSwaggerJson();
        }

        public void writeYamlHandler() {
            for (Map.Entry<String, Map<String, Object>> path : swaggerData.get("paths").entrySet()) {
                for (Map.Entry<String, Map<String, Object>> method : path.getValue().entrySet()) {
                    writeYaml(convertToYamlCase(method.getValue()));
                }
            }
        }
    }
    """
    def __init__(self):
        self._data = self.get_swagger_json()

    @classmethod
    def get_swagger_json(cls):
        """
        读取 Swagger OpenAPI JSON 文件

        Returns:
            dict: Swagger JSON 数据

        Raises:
            FileNotFoundError: 如果文件不存在
        """
        try:
            with open('./file/test_OpenAPI.json', "r", encoding='utf-8') as f:
                row_data = json.load(f)
                return row_data
        except FileNotFoundError:
            raise FileNotFoundError("文件路径不存在，请重新输入")

    def get_allure_epic(self):
        """
        从 Swagger 信息中获取 Allure Epic 标签

        使用 Swagger 的 info.title 作为 Epic 名称。

        Returns:
            str: Epic 名称
        """
        _allure_epic = self._data['info']['title']
        return _allure_epic

    @classmethod
    def get_allure_feature(cls, value):
        """
        从 Swagger 方法信息中获取 Allure Feature 标签

        使用 Swagger 的 tags 作为 Feature。

        Args:
            value: Swagger 方法信息字典

        Returns:
            str: Feature 名称
        """
        _allure_feature = value['tags']
        return str(_allure_feature)

    @classmethod
    def get_allure_story(cls, value):
        """
        从 Swagger 方法信息中获取 Allure Story 标签

        使用 Swagger 的 summary 作为 Story。

        Args:
            value: Swagger 方法信息字典

        Returns:
            str: Story 名称
        """
        _allure_story = value['summary']
        return _allure_story

    @classmethod
    def get_case_id(cls, value):
        """
        生成用例 ID

        将 API 路径转换为合法的 YAML 键名。
        示例：/api/v1/user/login -> 01_api_v1_user_login

        Args:
            value: API 路径

        Returns:
            str: 用例 ID
        """
        _case_id = value.replace("/", "_")
        return "01" + _case_id

    @classmethod
    def get_detail(cls, value):
        """
        生成用例描述

        在 Swagger summary 前加 "测试" 前缀。

        Args:
            value: Swagger 方法信息字典

        Returns:
            str: 用例描述
        """
        _get_detail = value['summary']
        return "测试" + _get_detail

    @classmethod
    def get_request_type(cls, value, headers):
        """
        根据 Swagger 参数信息推断请求类型

        推断逻辑：
        - 参数在 query 中 -> params
        - Content-Type 为 form-urlencoded/form-data -> data
        - Content-Type 为 json -> json
        - Content-Type 为 octet-stream -> file

        Args:
            value: Swagger 方法信息字典
            headers: 请求头字典

        Returns:
            str: 请求类型（params/data/json/file）
        """
        if jsonpath(obj=value, expr="$.parameters") is not False:
            _parameters = value['parameters']
            if _parameters[0]['in'] == 'query':
                return "params"
            else:
                if 'application/x-www-form-urlencoded' or 'multipart/form-data' in headers:
                    return "data"
                elif 'application/json' in headers:
                    return "json"
                elif 'application/octet-stream' in headers:
                    return "file"
                else:
                    return "data"

    @classmethod
    def get_case_data(cls, value):
        """
        从 Swagger 参数中提取请求体数据模板

        将所有非 header 参数的字段名提取出来，值设为 None，
        供用户后续在 YAML 中填写实际测试值。

        Args:
            value: Swagger 方法信息字典

        Returns:
            dict: 请求数据模板；如果没有参数则返回 None
        """
        _dict = {}
        if jsonpath(obj=value, expr="$.parameters") is not False:
            _parameters = value['parameters']
            for i in _parameters:
                if i['in'] == 'header':
                    ...  # header 参数单独处理
                else:
                    _dict[i['name']] = None
        else:
            return None
        return _dict

    @classmethod
    def yaml_cases(cls, data: Dict, file_path: str) -> None:
        """
        将用例数据写入 YAML 文件

        按 API 路径创建目录结构，并生成 YAML 用例文件。

        Args:
            data: 用例数据字典
            file_path: API 路径（如 /api/v1/user/login）
        """
        # 构建 YAML 文件的绝对路径
        _file_path = ensure_path_sep("\\data\\" + file_path[1:].replace("/", os.sep) + '.yaml')
        # 创建目录
        _file = _file_path.split(os.sep)[:-1]
        _dir_path = ''
        for i in _file:
            _dir_path += i + os.sep
        try:
            os.makedirs(_dir_path)
        except FileExistsError:
            ...  # 目录已存在，忽略
        # 追加写入 YAML 数据
        with open(_file_path, "a", encoding="utf-8") as file:
            yaml.dump(data, file, Dumper=yaml.RoundTripDumper, allow_unicode=True)
            file.write('\n')

    @classmethod
    def get_headers(cls, value):
        """
        从 Swagger 方法信息中提取请求头

        提取 consumes 中的 Content-Type 和 header 参数。

        Args:
            value: Swagger 方法信息字典

        Returns:
            dict: 请求头字典
        """
        _headers = {}
        if jsonpath(obj=value, expr="$.consumes") is not False:
            _headers = {"Content-Type": value['consumes'][0]}
        if jsonpath(obj=value, expr="$.parameters") is not False:
            for i in value['parameters']:
                if i['in'] == 'header':
                    _headers[i['name']] = None
        else:
            _headers = None
        return _headers

    def write_yaml_handler(self):
        """
        主执行方法：遍历所有 API 并生成 YAML 用例

        【执行流程】
        1. 从 Swagger JSON 中获取所有 paths
        2. 遍历每个路径下的每个 HTTP 方法
        3. 构建用例数据字典
        4. 写入 YAML 文件

        Java 类比：
        public void writeYamlHandler() {
            Map<String, Map<String, Object>> paths = swaggerData.get("paths");
            for (Map.Entry<String, Map<String, Object>> pathEntry : paths.entrySet()) {
                for (Map.Entry<String, Object> methodEntry : pathEntry.getValue().entrySet()) {
                    Map<String, Object> yamlCase = convertToYamlCase(methodEntry);
                    writeYaml(yamlCase, pathEntry.getKey());
                }
            }
        }
        """
        _api_data = self._data['paths']
        for key, value in _api_data.items():
            for k, v in value.items():
                yaml_data = {
                    "case_common": {
                        "allureEpic": self.get_allure_epic(),
                        "allureFeature": self.get_allure_feature(v),
                        "allureStory": self.get_allure_story(v)
                    },
                    self.get_case_id(key): {
                        "host": "${{host()}}",
                        "url": key,
                        "method": k,
                        "detail": self.get_detail(v),
                        "headers": self.get_headers(v),
                        "requestType": self.get_request_type(v, self.get_headers(v)),
                        "is_run": None,
                        "data": self.get_case_data(v),
                        "dependence_case": False,
                        "assert": {"status_code": 200},
                        "sql": None
                    }
                }
                self.yaml_cases(yaml_data, file_path=key)


if __name__ == '__main__':
    SwaggerForYaml().write_yaml_handler()
