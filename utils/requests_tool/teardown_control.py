#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2022/5/23 14:22
# @Author  : 余少琪
# @Email   : 1603453211@qq.com
# @File    : teardownControl
# @Description: 请求后置处理器
#
# 【文件作用】
# TearDownHandler 负责在测试用例执行完毕后进行清理操作。
# 典型场景：
# - 测试完"添加商品"后，自动调用"删除商品"接口清理数据
# - 测试完成后，执行 DELETE SQL 清理数据库中的测试数据
#
# 【核心概念】
# teardown 在 YAML 中定义了用例执行完毕后需要执行的操作。
# 它包含两个子部分：
# 1. param_prepare（参数准备）: 先执行后置用例，然后从其响应中提取数据写入缓存
#    -> 关注点：获取后置接口 B 的响应 / 当前接口 A 的响应
# 2. send_request（发送请求）: 先准备参数，然后发起后置请求
#    -> 关注点：用当前接口 A 的响应数据来参数化后置请求
#
# 【为什么需要区分 param_prepare 和 send_request？】
# 假设用例 A 执行后，需要调用用例 B 进行清理：
# - param_prepare: 先调用 B，然后从 B 的响应中提取数据缓存
#   （或从 A 的响应中提取数据缓存）
# - send_request: 从 A 的响应中提取数据，用来参数化 B 的请求
#
# 简单来说：
# - param_prepare = 先执行用例，再提取响应数据
# - send_request = 先提取数据参数化，再执行用例
#
# 【Java 对比说明】
# - @AfterMethod（TestNG）或 @AfterEach（JUnit 5）
# - 类似于 Java 中的 try-finally 块中的清理逻辑
import ast
import json
from typing import Dict, Text
from jsonpath import jsonpath
from utils.requests_tool.request_control import RequestControl
from utils.read_files_tools.regular_control import cache_regular, sql_regular, regular
from utils.other_tools.jsonpath_date_replace import jsonpath_replace
from utils.mysql_tool.mysql_control import MysqlDB
from utils.logging_tool.log_control import WARNING
from utils.other_tools.models import ResponseData, TearDown, SendRequest, ParamPrepare
from utils.other_tools.exceptions import JsonpathExtractionFailed, ValueNotFoundError
from utils.cache_process.cache_control import CacheHandler
from utils import config


class TearDownHandler:
    """
    YAML 格式后置请求处理器

    核心职责：
    - 在用例执行完毕后，执行 teardown 中定义的清理操作
    - 支持从响应/请求/缓存中提取数据用于后置请求的参数化
    - 执行后置 SQL 清理数据库数据

    Java 类比：
    public class TearDownHandler {
        private ResponseData response;

        public TearDownHandler(ResponseData res) {
            this.response = res;
        }

        public void teardownHandle() { ... }
    }
    """

    def __init__(self, res: "ResponseData"):
        """
        初始化后置处理器

        Args:
            res: 当前测试用例的响应数据（ResponseData 对象）
        """
        self._res = res

    @classmethod
    def jsonpath_replace_data(cls, replace_key: Text, replace_value: Dict) -> Text:
        """
        通过 JSONPath 定位需要替换的数据位置，生成 Python 赋值语句

        这个方法将 YAML 中的 replace_key（如 "$.data.id"）
        转换为 Python 可执行的赋值语句。

        Args:
            replace_key: JSONPath 替换路径（如 "$.data.id"）
            replace_value: 要替换的值

        Returns:
            str: Python 赋值语句（如 "_teardown_case['data']['id'] = 123"）

        Java 类比：
        类似于构建动态赋值语句：
        String assignment = "_teardownCase" + pathToExpression(replaceKey) + " = " + replaceValue;
        """
        _change_data = replace_key.split(".")
        # jsonpath 数据解析：将 $.data.id 转为 _teardown_case['data']['id']
        _new_data = jsonpath_replace(
            change_data=_change_data,
            key_name='_teardown_case',
            data_switch=False
        )

        # 根据替换值的类型，决定是否需要加引号
        if not isinstance(replace_value, str):
            _new_data += f" = {replace_value}"  # 非字符串，直接赋值
        # 最终提取到的数据，转换成 _teardown_case[xxx][xxx]
        else:
            _new_data += f" = '{replace_value}'"  # 字符串，加引号
        return _new_data

    @classmethod
    def get_cache_name(cls, replace_key: Text, resp_case_data: Dict) -> None:
        """
        从 replace_key 中提取缓存键名，并将数据写入缓存

        当 replace_key 包含 "$set_cache{xxx}" 语法时，
        表示需要将提取的数据存入缓存。

        Args:
            replace_key: 替换路径（可能包含 $set_cache{缓存名} 语法）
            resp_case_data: 要缓存的数据

        示例：
        replace_key = "$set_cache{token}" -> 缓存键名为 "token"
        """
        if "$set_cache{" in replace_key and "}" in replace_key:
            # 解析 $set_cache{xxx} 中的 xxx
            start_index = replace_key.index("$set_cache{")
            end_index = replace_key.index("}", start_index)
            old_value = replace_key[start_index:end_index + 2]
            cache_name = old_value[11:old_value.index("}")]
            # 将数据写入缓存
            CacheHandler.update_cache(cache_name=cache_name, value=resp_case_data)

    @classmethod
    def regular_testcase(cls, teardown_case: Dict) -> Dict:
        """
        处理测试用例中的动态数据

        将 teardown 用例中的动态表达式（如 $cache{xxx}）
        解析为实际的值。

        Args:
            teardown_case: 后置用例数据

        Returns:
            Dict: 解析动态表达式后的用例数据
        """
        test_case = regular(str(teardown_case))
        test_case = ast.literal_eval(cache_regular(str(test_case)))
        return test_case

    @classmethod
    def teardown_http_requests(cls, teardown_case: Dict) -> "ResponseData":
        """
        发送后置 HTTP 请求

        将解析后的后置用例数据交给 RequestControl 执行。
        dependent_switch=False 表示不处理后置请求的接口依赖，避免循环依赖。

        Args:
            teardown_case: 解析后的后置用例数据

        Returns:
            ResponseData: 后置请求的响应
        """
        test_case = cls.regular_testcase(teardown_case)
        res = RequestControl(test_case).http_request(
            dependent_switch=False  # 关闭依赖处理，避免循环依赖
        )
        return res

    def dependent_type_response(self, teardown_case_data: "SendRequest", resp_data: Dict) -> Text:
        """
        从当前用例的响应内容中提取数据用于替换

        当依赖类型为 "response" 时，从当前用例（用例 A）的响应中
        通过 JSONPath 提取数据，用于参数化后置请求。

        Args:
            teardown_case_data: teardown 中的请求定义
            resp_data: 当前用例的响应数据

        Returns:
            str: 生成的 Python 赋值语句

        Raises:
            JsonpathExtractionFailed: 如果 JSONPath 提取失败
        """
        _replace_key = teardown_case_data.replace_key
        # 从响应数据中通过 JSONPath 提取值
        _response_dependent = jsonpath(
            obj=resp_data,
            expr=teardown_case_data.jsonpath
        )
        # 如果提取到数据，则进行替换
        if _response_dependent is not False:
            _resp_case_data = _response_dependent[0]
            data = self.jsonpath_replace_data(
                replace_key=_replace_key,
                replace_value=_resp_case_data
            )
        else:
            raise JsonpathExtractionFailed(
                f"jsonpath提取失败，替换内容: {resp_data} \n"
                f"jsonpath: {teardown_case_data.jsonpath}"
            )
        return data

    def dependent_type_request(self, teardown_case_data: Dict, request_data: Dict) -> None:
        """
        从当前用例的请求内容中提取数据写入缓存

        当依赖类型为 "request" 时，从当前用例（用例 A）的请求参数中
        通过 JSONPath 提取数据，并存入缓存。

        Args:
            teardown_case_data: teardown 中的请求定义
            request_data: 当前用例的请求参数

        Raises:
            JsonpathExtractionFailed: 如果 JSONPath 提取失败
            ValueNotFoundError: 如果 teardown 中缺少 set_value 参数
        """
        try:
            _request_set_value = teardown_case_data['set_value']
            # 从请求数据中通过 JSONPath 提取值
            _request_dependent = jsonpath(
                obj=request_data,
                expr=teardown_case_data['jsonpath']
            )
            if _request_dependent is not False:
                _request_case_data = _request_dependent[0]
                # 将提取的值写入缓存
                self.get_cache_name(
                    replace_key=_request_set_value,
                    resp_case_data=_request_case_data
                )
            else:
                raise JsonpathExtractionFailed(
                    f"jsonpath提取失败，替换内容: {request_data} \n"
                    f"jsonpath: {teardown_case_data['jsonpath']}"
                )
        except KeyError as exc:
            raise ValueNotFoundError("teardown中缺少set_value参数，请检查用例是否正确") from exc

    def dependent_self_response(
            self, teardown_case_data: "ParamPrepare",
            res: Dict, resp_data: Dict) -> None:
        """
        从后置用例（用例 B）自己的响应内容中提取数据

        当依赖类型为 "self_response" 时，从后置请求（用例 B）的响应中
        通过 JSONPath 提取数据，并存入缓存。

        Args:
            teardown_case_data: teardown 中的参数准备定义
            res: 后置请求的完整响应数据
            resp_data: 当前用例的响应数据（用于错误提示）

        Raises:
            JsonpathExtractionFailed: 如果 JSONPath 提取失败
            ValueNotFoundError: 如果 teardown 中缺少 set_cache 参数
        """
        try:
            _set_value = teardown_case_data.set_cache
            # 从后置请求的响应中通过 JSONPath 提取值
            _response_dependent = jsonpath(
                obj=res,
                expr=teardown_case_data.jsonpath
            )
            # 如果提取到数据
            if _response_dependent is not False:
                _resp_case_data = _response_dependent[0]
                # 拿到 set_cache，将数据写入缓存
                CacheHandler.update_cache(cache_name=_set_value, value=_resp_case_data)
                self.get_cache_name(
                    replace_key=_set_value,
                    resp_case_data=_resp_case_data
                )
            else:
                raise JsonpathExtractionFailed(
                    f"jsonpath提取失败，替换内容: {resp_data} \n"
                    f"jsonpath: {teardown_case_data.jsonpath}")
        except KeyError as exc:
            raise ValueNotFoundError("teardown中缺少set_cache参数，请检查用例是否正确") from exc

    @classmethod
    def dependent_type_cache(cls, teardown_case: "SendRequest") -> Text:
        """
        从缓存中获取数据用于后置请求的参数化

        当依赖类型为 "cache" 时，从全局缓存中读取之前存储的数据。

        Args:
            teardown_case: teardown 中的请求定义

        Returns:
            str: 生成的 Python 赋值语句

        注意：
        - 如果缓存名带有类型前缀（如 "int:userId"），则读取后按对应类型赋值
        - 类型前缀包括：int:, bool:, list:, dict:, tuple:, float:
        """
        if teardown_case.dependent_type == 'cache':
            _cache_name = teardown_case.cache_data
            _replace_key = teardown_case.replace_key
            # 通过 JSONPath 判断出需要替换数据的位置
            _change_data = _replace_key.split(".")
            _new_data = jsonpath_replace(
                change_data=_change_data,
                key_name='_teardown_case',
                data_switch=False
            )
            # jsonpath 数据解析
            value_types = ['int:', 'bool:', 'list:', 'dict:', 'tuple:', 'float:']
            if any(i in _cache_name for i in value_types) is True:
                # 有类型前缀：提取类型后的缓存名，并按原类型赋值
                _cache_data = CacheHandler.get_cache(_cache_name.split(':')[1])
                _new_data += f" = {_cache_data}"

            # 无类型前缀：按字符串赋值
            else:
                _cache_data = CacheHandler.get_cache(_cache_name)
                _new_data += f" = '{_cache_data}'"

            return _new_data

    def send_request_handler(
            self, data: "TearDown",
            resp_data: Dict, request_data: Dict) -> None:
        """
        后置请求处理（send_request 分支）

        【执行流程】
        1. 从缓存中获取后置用例的数据
        2. 遍历 send_request 中的每个请求定义
        3. 根据依赖类型（cache/response/request）处理数据替换
        4. 执行动态赋值语句
        5. 发送后置 HTTP 请求

        Args:
            data: teardown 定义
            resp_data: 当前用例的响应数据
            request_data: 当前用例的请求参数
        """
        _send_request = data.send_request
        _case_id = data.case_id
        # 从缓存中获取后置用例的数据
        _teardown_case = CacheHandler.get_cache(_case_id)
        for i in _send_request:
            # 从缓存中获取数据用于替换
            if i.dependent_type == 'cache':
                exec(self.dependent_type_cache(teardown_case=i))
            # 从当前用例的响应中提取数据用于替换
            if i.dependent_type == 'response':
                exec(
                    self.dependent_type_response(
                        teardown_case_data=i,
                        resp_data=resp_data)
                )
            # 从当前用例的请求中提取数据
            elif i.dependent_type == 'request':
                self.dependent_type_request(
                    teardown_case_data=i,
                    request_data=request_data
                )

        # 处理动态数据并发送后置请求
        test_case = self.regular_testcase(_teardown_case)
        self.teardown_http_requests(test_case)

    def param_prepare_request_handler(self, data: "TearDown", resp_data: Dict) -> None:
        """
        参数准备处理（param_prepare 分支）

        【执行流程】
        1. 从缓存中获取后置用例的数据
        2. 先发送后置 HTTP 请求
        3. 从后置请求的响应中提取数据写入缓存（self_response 类型）

        与 send_request_handler 的区别：
        - param_prepare：先发送请求，再从请求响应中提取数据
        - send_request：先提取数据参数化，再发送请求

        Args:
            data: teardown 定义
            resp_data: 当前用例的响应数据
        """
        _case_id = data.case_id
        # 从缓存中获取后置用例的数据
        _teardown_case = CacheHandler.get_cache(_case_id)
        _param_prepare = data.param_prepare
        # 先发送后置请求
        res = self.teardown_http_requests(_teardown_case)
        for i in _param_prepare:
            # 判断请求类型为 self_response：从后置请求自己的响应中提取数据
            if i.dependent_type == 'self_response':
                self.dependent_self_response(
                    teardown_case_data=i,
                    resp_data=resp_data,
                    res=json.loads(res.response_data)
                )

    def teardown_handle(self) -> None:
        """
        后置处理主入口

        【为什么需要区分 param_prepare 和 send_request？】
        假设有用例 A，teardown 中需要执行用例 B 进行清理。

        用户可能需要：
        1. 获取用例 B 的响应内容（需要先发送 B 请求）
        2. 获取用例 A 的响应内容（A 已经执行过，不需要再发送请求）

        因此通过关键词区分：
        - param_prepare：前置准备，先发送请求，再获取 B 的响应数据
        - send_request：发送请求，用 A 的响应数据来参数化 B 的请求

        【执行流程】
        1. 获取用例的 teardown 定义
        2. 遍历每个 teardown 项
        3. 根据是否存在 param_prepare 或 send_request 分别处理
        4. 执行后置 SQL 清理

        Java 类比：
        public void teardownHandle() {
            List<TearDown> teardownData = response.getTeardown();
            if (teardownData != null) {
                for (TearDown td : teardownData) {
                    if (td.getParamPrepare() != null) {
                        handleParamPrepare(td, response.getResponseData());
                    } else if (td.getSendRequest() != null) {
                        handleSendRequest(td, response.getResponseData(), request.getData());
                    }
                }
            }
            teardownSql();
        }
        """
        # 获取用例信息
        _teardown_data = self._res.teardown
        # 获取接口的响应内容
        _resp_data = self._res.response_data
        # 获取接口的请求参数
        _request_data = self._res.yaml_data.data

        # 判断如果没有 teardown，则直接执行 teardown_sql
        if _teardown_data is not None:
            # 循环 teardown 中的每个接口
            for _data in _teardown_data:
                if _data.param_prepare is not None:
                    # 处理参数准备分支
                    self.param_prepare_request_handler(
                        data=_data,
                        resp_data=json.loads(_resp_data)
                    )
                elif _data.send_request is not None:
                    # 处理发送请求分支
                    self.send_request_handler(
                        data=_data,
                        request_data=_request_data,
                        resp_data=json.loads(_resp_data)
                    )
        # 执行后置 SQL
        self.teardown_sql()

    def teardown_sql(self) -> None:
        """
        执行后置 SQL 清理语句

        在测试用例执行完毕后，通过 SQL 删除数据库中产生的测试数据。

        典型场景：
        - 测试完"创建用户"后，执行 "DELETE FROM user WHERE username='test_user'"

        注意：
        - 只在数据库开关开启时执行
        - SQL 中可以引用当前接口的响应数据（如通过 JSONPath 提取 ID）
        """
        sql_data = self._res.teardown_sql
        _response_data = self._res.response_data
        if sql_data is not None:
            for i in sql_data:
                if config.mysql_db.switch:
                    # 解析 SQL 中的动态表达式（如引用响应数据）
                    _sql_data = sql_regular(value=i, res=json.loads(_response_data))
                    # 执行 SQL 语句
                    MysqlDB().execute(cache_regular(_sql_data))
                else:
                    WARNING.logger.warning(
                        "程序中检查到您数据库开关为关闭状态，已为您跳过删除sql: %s", i
                    )
