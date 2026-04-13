#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/3/28 14:18
# @Author : 余少琪
# @Description: 断言引擎 —— 验证接口响应和数据库数据
#
# 【文件作用】
# Assert 类负责根据 YAML 中定义的断言规则，验证接口响应数据和数据库查询结果。
# 支持两种断言模式：
# 1. JSON 响应断言：验证 HTTP 响应的 JSON 数据
# 2. SQL 数据库断言：验证数据库查询结果与响应数据的一致性
#
# 【断言流程】
# 1. 遍历 YAML 中定义的所有断言规则
# 2. 通过 JSONPath 从响应中提取目标字段值
# 3. 根据断言类型（==, >, contains 等）调用对应的比较函数
# 4. 如果断言类型为 SQL，则额外验证数据库数据
#
# 【Java 对比说明】
# - jsonpath 类似于 Java 的 JsonPath.read(json, "$.code")
# - load_module_functions 类似于 Java 的反射获取方法
# - self.functions_mapping[name]() 类似于 Java 的 method.invoke()
import ast
import json
from typing import Text, Dict, Any, Union
from jsonpath import jsonpath
from utils.other_tools.models import AssertMethod
from utils.logging_tool.log_control import ERROR, WARNING
from utils.read_files_tools.regular_control import cache_regular
from utils.other_tools.models import load_module_functions
from utils.assertion import assert_type
from utils.other_tools.exceptions import JsonpathExtractionFailed, SqlNotFound, AssertTypeError
from utils import config


class Assert:
    """
    断言执行引擎

    核心职责：
    - 解析 YAML 中的断言规则
    - 通过 JSONPath 从响应中提取目标值
    - 执行断言比较（支持 15+ 种断言类型）
    - 支持 SQL 数据库断言

    Java 类比：
    public class Assert {
        private Map<String, Object> assertData;
        private Map<String, Method> functionsMapping;

        public Assert(Map<String, Object> assertData) {
            this.assertData = assertData;
            this.functionsMapping = loadModuleFunctions(AssertType.class);
        }

        public void assertEquality(String responseData, Map<String, Object> sqlData, int statusCode) { ... }
    }
    """

    def __init__(self, assert_data: Dict):
        """
        初始化断言引擎

        Args:
            assert_data: YAML 中定义的断言数据（字典格式）

        初始化过程：
        1. 解析动态表达式（cache_regular）
        2. 将字符串转为 Python 对象（ast.literal_eval）
        3. 加载 assert_type 模块中所有的断言比较函数
        """
        # 解析断言数据：支持动态表达式（如 $cache{xxx}）
        self.assert_data = ast.literal_eval(cache_regular(str(assert_data)))
        # 加载 assert_type 模块中的所有断言函数
        # functions_mapping 的格式：{"equals": <function equals>, "contains": <function contains>, ...}
        self.functions_mapping = load_module_functions(assert_type)

    @staticmethod
    def _check_params(response_data: Text, sql_data: Union[Dict, None]) -> bool:
        """
        校验断言参数：确保 sql_data 的类型是字典

        Args:
            response_data: 响应数据（JSON 字符串）
            sql_data: 数据库查询结果

        Returns:
            bool: 校验通过返回 True

        Raises:
            ValueError: 如果 sql_data 不是字典类型
        """
        if (response_data and sql_data) is not False:
            if not isinstance(sql_data, dict):
                raise ValueError(
                    "断言失败，response_data、sql_data的数据类型必须要是字典类型，"
                    "请检查接口对应的数据是否正确\n"
                    f"sql_data: {sql_data}, 数据类型: {type(sql_data)}\n"
                )
        return True

    @staticmethod
    def res_sql_data_bytes(res_sql_data: Any) -> Text:
        """
        处理 MySQL 查询结果中的 bytes 类型数据

        MySQL 驱动查询出来的数据可能是 bytes 类型，需要转为 str 才能比较。

        Args:
            res_sql_data: MySQL 查询结果值

        Returns:
            str: 转换后的字符串
        """
        if isinstance(res_sql_data, bytes):
            res_sql_data = res_sql_data.decode('utf=8')
        return res_sql_data

    def sql_switch_handle(
            self, sql_data: Dict, assert_value: Any, key: Text,
            values: Any, resp_data: Dict, message: Text) -> None:
        """
        SQL 数据库断言处理

        当断言的 AssertType 为 "SQL" 时，执行数据库数据验证：
        1. 检查数据库开关是否开启
        2. 通过 JSONPath 从 SQL 查询结果中提取目标值
        3. 将 bytes 类型转为 str
        4. 调用对应的断言比较函数，比较响应值与数据库值

        Args:
            sql_data: SQL 查询结果
            assert_value: JSONPath 表达式（用于从 SQL 结果中提取值）
            key: 断言规则的键名
            values: 断言规则的完整内容
            resp_data: 接口响应数据（通过 JSONPath 提取后的值）
            message: 自定义错误消息

        Raises:
            JsonpathExtractionFailed: 如果 JSONPath 提取失败
            SqlNotFound: 如果用例中没有定义 SQL 查询
        """
        # 判断数据库开关是否为关闭状态
        if config.mysql_db.switch is False:
            # 数据库关闭时，跳过此断言并记录警告日志
            WARNING.logger.warning(
                "检测到数据库状态为关闭状态，程序已为您跳过此断言，断言值:%s", values
            )

        # 数据库开关为开启状态
        if config.mysql_db.switch:
            # 走正常 SQL 断言逻辑
            if sql_data != {'sql': None}:
                # 通过 JSONPath 从 SQL 查询结果中提取目标值
                res_sql_data = jsonpath(sql_data, assert_value)
                if res_sql_data is False:
                    raise JsonpathExtractionFailed(
                        f"数据库断言内容jsonpath提取失败， 当前jsonpath内容: {assert_value}\n"
                        f"数据库返回内容: {sql_data}"
                    )

                # 判断 MySQL 查询出来的数据类型，如果是 bytes 类型则转换为 str
                res_sql_data = self.res_sql_data_bytes(res_sql_data[0])

                # 根据断言类型获取对应的比较函数名
                # 例如：assert_data[key]['type'] = "==" -> AssertMethod("==").name = "equals"
                name = AssertMethod(self.assert_data[key]['type']).name
                # 调用对应的断言函数：比较响应值与数据库值
                self.functions_mapping[name](resp_data[0], res_sql_data, str(message))

            # 用例定义了 SQL 断言，但没有填写 SQL 语句
            else:
                raise SqlNotFound("请在用例中添加您要查询的SQL语句。")

    def assert_type_handle(
            self, assert_types: Union[Text, None], sql_data: Union[Dict, None],
            assert_value: Any, key: Text, values: Dict,
            resp_data: Any, message: Text) -> None:
        """
        断言类型分发处理器

        根据 AssertType 的值决定执行哪种断言模式：
        - "SQL" -> 执行 SQL 数据库断言
        - None -> 执行普通的 JSON 响应断言

        Args:
            assert_types: 断言类型（"SQL" 或 None）
            sql_data: SQL 查询结果
            assert_value: 预期值
            key: 断言规则的键名
            values: 断言规则的完整内容
            resp_data: 响应数据（通过 JSONPath 提取后的值）
            message: 自定义错误消息

        Raises:
            AssertTypeError: 如果 AssertType 不是 "SQL" 或 None
        """
        # 判断断言类型为 SQL
        if assert_types == 'SQL':
            self.sql_switch_handle(
                sql_data=sql_data,
                assert_value=assert_value,
                key=key,
                values=values,
                resp_data=resp_data,
                message=message
            )

        # 判断 AssertType 为空，则走响应断言（最常见的情况）
        elif assert_types is None:
            # 获取断言类型对应的函数名
            name = AssertMethod(self.assert_data[key]['type']).name
            # 调用断言函数：比较实际值与预期值
            self.functions_mapping[name](resp_data[0], assert_value, message)
        else:
            raise AssertTypeError("断言失败，目前只支持数据库断言和响应断言")

    @classmethod
    def _message(cls, value):
        """
        从断言规则中提取自定义错误消息

        如果断言规则中定义了 message 字段，则使用该消息作为断言失败时的提示。

        Args:
            value: 断言规则字典

        Returns:
            str: 自定义消息，如果没有定义则返回空字符串
        """
        _message = ""
        if jsonpath(obj=value, expr="$.message") is not False:
            _message = value['message']
        return _message

    def assert_equality(self, response_data: Text, sql_data: Dict, status_code: int) -> None:
        """
        断言执行主入口

        【执行流程】
        1. 校验参数（response_data 和 sql_data 的类型）
        2. 遍历所有断言规则
        3. 如果是 status_code 断言，直接比较 HTTP 状态码
        4. 否则，通过 JSONPath 从响应中提取目标值
        5. 根据断言类型（SQL/响应）调用对应的处理方法

        【YAML 断言示例】
        assert:
          status_code: 200                    # HTTP 状态码断言
          code_eq:                             # 自定义断言规则名
            jsonpath: "$.code"                 # 从响应中提取 $.code
            type: "=="                         # 断言类型：等于
            value: 0                           # 预期值
            AssertType: null                   # 断言分类（null=响应断言）
            message: "返回码不正确"             # 自定义错误消息

        Args:
            response_data: 接口响应数据（JSON 字符串）
            sql_data: SQL 查询结果
            status_code: HTTP 状态码

        Raises:
            JsonpathExtractionFailed: 如果 JSONPath 提取失败
            AssertionError: 如果断言比较失败（由 assert 语句触发）

        Java 类比：
        public void assertAll(String responseData, Map<String, Object> sqlData, int statusCode) {
            checkParams(responseData, sqlData);
            for (Map.Entry<String, Object> entry : assertData.entrySet()) {
                if ("status_code".equals(entry.getKey())) {
                    assertEquals(statusCode, entry.getValue());
                } else {
                    // Extract value via JSONPath, then compare
                    String jsonpath = assertData.get("jsonpath");
                    Object expectedValue = assertData.get("value");
                    Object actualValue = JsonPath.read(responseData, jsonpath);
                    assertCompare(actualValue, expectedValue, assertData.get("type"));
                }
            }
        }
        """
        # 判断数据类型是否正确
        if self._check_params(response_data, sql_data) is not False:
            # 遍历所有断言规则
            for key, values in self.assert_data.items():
                # 特殊处理：HTTP 状态码断言
                if key == "status_code":
                    assert status_code == values
                else:
                    # 获取预期值
                    assert_value = self.assert_data[key]['value']
                    # 获取 JSONPath 表达式
                    assert_jsonpath = self.assert_data[key]['jsonpath']
                    # 获取断言类型分类（SQL/响应）
                    assert_types = self.assert_data[key]['AssertType']
                    # 从响应中通过 JSONPath 提取实际值
                    resp_data = jsonpath(json.loads(response_data), assert_jsonpath)
                    # 获取自定义错误消息
                    message = self._message(value=values)

                    # JSONPath 提取成功
                    if resp_data is not False:
                        # 根据断言类型分发处理
                        self.assert_type_handle(
                            assert_types=assert_types,
                            sql_data=sql_data,
                            assert_value=assert_value,
                            key=key,
                            values=values,
                            resp_data=resp_data,
                            message=message
                        )
                    else:
                        ERROR.logger.error("JsonPath值获取失败 %s ", assert_jsonpath)
                        raise JsonpathExtractionFailed(f"JsonPath值获取失败 {assert_jsonpath}")


if __name__ == '__main__':
    pass
