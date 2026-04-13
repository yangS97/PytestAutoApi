#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/3/28 16:08
# @Author : 余少琪
# @Description: 接口数据依赖处理器
#
# 【文件作用】
# 在多接口测试场景中，后一个接口往往需要前一个接口的返回数据作为入参。
# DependentCase 类负责处理这种接口间的依赖关系。
#
# 【核心概念】
# 依赖类型（DependentType）：
# - response: 从被依赖接口的响应中提取数据
# - request: 从被依赖接口的请求参数中提取数据
# - sqlData: 从数据库查询结果中提取数据
#
# 【工作流程】
# 1. 检查当前用例是否定义了接口依赖（dependence_case = true）
# 2. 遍历所有被依赖的用例（dependence_case_data）
# 3. 对被依赖用例发起请求（如果还没执行过，先执行）
# 4. 通过 JSONPath 从响应/请求/SQL 结果中提取目标值
# 5. 将提取的值写入缓存（可选）
# 6. 将提取的值替换到当前用例的对应位置
#
# 【YAML 依赖示例】
# - name: 创建订单后查询订单详情
#   dependence_case: true
#   dependence_case_data:
#     - case_id: "create_order_001"     # 依赖创建订单接口
#       dependent_data:
#         - dependent_type: "response"   # 从响应中提取
#           jsonpath: "$.data.orderId"   # 提取 orderId
#           replace_key: "$.data.id"     # 替换到当前用例的 data.id 字段
#
# 【Java 对比说明】
# - JSONPath 类似于 Java 的 com.jayway.jsonpath.JsonPath
# - exec() 动态赋值类似于 Java 的反射字段赋值
# - CacheHandler 类似于 Java 的 ConcurrentHashMap 静态缓存
import ast
import json
from typing import Text, Dict, Union, List
from jsonpath import jsonpath
from utils.requests_tool.request_control import RequestControl
from utils.mysql_tool.mysql_control import SetUpMySQL
from utils.read_files_tools.regular_control import regular, cache_regular
from utils.other_tools.jsonpath_date_replace import jsonpath_replace
from utils.logging_tool.log_control import WARNING
from utils.other_tools.models import DependentType
from utils.other_tools.models import TestCase, DependentCaseData, DependentData
from utils.other_tools.exceptions import ValueNotFoundError
from utils.cache_process.cache_control import CacheHandler
from utils import config


class DependentCase:
    """
    接口依赖数据处理引擎

    核心职责：
    - 解析 YAML 中的接口依赖定义
    - 从被依赖接口的响应/请求/SQL 结果中提取数据
    - 将提取的数据替换到当前用例的对应位置

    Java 类比：
    public class DependentCase {
        private TestCase yamlCase;

        public DependentCase(TestCase dependentYamlCase) {
            this.yamlCase = dependentYamlCase;
        }

        public void getDependentData() { ... }
    }
    """

    def __init__(self, dependent_yaml_case: TestCase):
        """
        初始化依赖处理器

        Args:
            dependent_yaml_case: 当前测试用例的数据（TestCase 对象）
        """
        self.__yaml_case = dependent_yaml_case

    @classmethod
    def get_cache(cls, case_id: Text) -> Dict:
        """
        从缓存中获取已执行的用例数据

        被依赖的用例必须先执行，其响应数据会被存入缓存。
        这个方法从缓存中读取这些数据。

        Args:
            case_id: 被依赖用例的唯一标识

        Returns:
            Dict: 缓存中的用例数据

        Java 类比：
        public static Map<String, Object> getCache(String caseId) {
            return CacheHandler.getCache(caseId);
        }
        """
        _case_data = CacheHandler.get_cache(case_id)
        return _case_data

    @classmethod
    def jsonpath_data(cls, obj: Dict, expr: Text) -> list:
        """
        通过 JSONPath 从对象中提取数据

        Args:
            obj: 被提取的数据对象（如接口响应的 JSON）
            expr: JSONPath 表达式（如 "$.data.token"）

        Returns:
            list: 提取到的值列表（JSONPath 总是返回列表）

        Raises:
            ValueNotFoundError: 如果 JSONPath 提取失败

        示例：
        obj = {"data": {"token": "abc123", "userId": 42}}
        expr = "$.data.token"
        返回：["abc123"]

        Java 类比：
        List<Object> result = JsonPath.read(obj, expr);
        if (result.isEmpty()) {
            throw new ValueNotFoundError(...);
        }
        """
        _jsonpath_data = jsonpath(obj, expr)
        # 判断是否正常提取到数据，如果未提取到（返回 False），则抛异常
        if _jsonpath_data is False:
            raise ValueNotFoundError(
                f"jsonpath提取失败！\n 提取的数据: {obj} \n jsonpath规则: {expr}"
            )
        return _jsonpath_data

    @classmethod
    def set_cache_value(cls, dependent_data: "DependentData") -> Union[Text, None]:
        """
        检查依赖数据中是否定义了缓存键

        如果定义了 set_cache，则提取到的数据会被存入全局缓存，
        供后续其他用例引用。

        Args:
            dependent_data: 依赖数据定义对象

        Returns:
            str: 缓存键名；如果未定义则返回 None
        """
        try:
            return dependent_data.set_cache
        except KeyError:
            return None

    @classmethod
    def replace_key(cls, dependent_data: "DependentData"):
        """
        获取需要替换的字段路径

        replace_key 定义了从被依赖接口提取的数据应该替换到当前用例的哪个位置。

        Args:
            dependent_data: 依赖数据定义对象

        Returns:
            str: 替换路径（如 "$.data.id"）；如果未定义则返回 None
        """
        try:
            _replace_key = dependent_data.replace_key
            return _replace_key
        except KeyError:
            return None

    def url_replace(self, replace_key: Text, jsonpath_dates: Dict, jsonpath_data: list) -> None:
        """
        替换 URL 中的动态参数

        处理场景：有些接口的参数直接在 URL 路径中，没有参数名称。
        例如：/api/v1/work/spu/approval/spuApplyDetails/{id}

        YAML 中可以使用 $url_params{id} 语法来标记需要替换的位置：
        url: /api/v1/work/spu/approval/spuApplyDetails/$url_params{id}

        Args:
            replace_key: 用例中需要替换的键（如 "$url_params{id}" 或 "$.data.id"）
            jsonpath_dates: 存储所有替换数据的字典
            jsonpath_data: JSONPath 解析出来的值列表

        Java 类比：
        private void replaceUrlParam(String replaceKey, Map<String, Object> dates, List<Object> values) {
            if (replaceKey.contains("$url_param")) {
                String url = yamlCase.getUrl().replace(replaceKey, values.get(0).toString());
                dates.put("$.url", url);
            } else {
                dates.put(replaceKey, values.get(0));
            }
        }
        """
        if "$url_param" in replace_key:
            # 替换 URL 路径中的动态参数
            _url = self.__yaml_case.url.replace(replace_key, str(jsonpath_data[0]))
            jsonpath_dates['$.url'] = _url
        else:
            # 普通的 JSON 字段替换
            jsonpath_dates[replace_key] = jsonpath_data[0]

    def _dependent_type_for_sql(
            self, setup_sql: List, dependence_case_data: "DependentCaseData",
            jsonpath_dates: Dict) -> None:
        """
        处理 SQL 数据依赖

        当依赖的 case_id 为 "self" 时，表示从当前用例的前置 SQL 查询结果
        中提取数据，而不是从其他接口的响应中提取。

        典型场景：
        - 先查询数据库获取某个测试用的 ID
        - 然后用这个 ID 去调用接口验证行为

        Args:
            setup_sql: 前置 SQL 语句列表
            dependence_case_data: 依赖的数据定义
            jsonpath_dates: 存储所有替换数据的字典

        Java 类比：
        private void handleSqlDependency(List<String> setupSql,
                                         DependentCaseData depData,
                                         Map<String, Object> dates) { ... }
        """
        # 判断依赖数据类型：依赖 SQL 中的数据
        if setup_sql is not None:
            if config.mysql_db.switch:
                # 解析 SQL 语句中的动态表达式
                setup_sql = ast.literal_eval(cache_regular(str(setup_sql)))
                # 执行 SQL 查询
                sql_data = SetUpMySQL().setup_sql_data(sql=setup_sql)
                # 遍历依赖数据定义
                dependent_data = dependence_case_data.dependent_data
                for i in dependent_data:
                    _jsonpath = i.jsonpath
                    # 从 SQL 结果中通过 JSONPath 提取值
                    jsonpath_data = self.jsonpath_data(obj=sql_data, expr=_jsonpath)
                    _set_value = self.set_cache_value(i)
                    _replace_key = self.replace_key(i)
                    # 如果定义了缓存键，将值写入缓存
                    if _set_value is not None:
                        CacheHandler.update_cache(cache_name=_set_value, value=jsonpath_data[0])
                    # 如果定义了替换键，将值加入替换字典
                    if _replace_key is not None:
                        jsonpath_dates[_replace_key] = jsonpath_data[0]
                        self.url_replace(
                            replace_key=_replace_key,
                            jsonpath_dates=jsonpath_dates,
                            jsonpath_data=jsonpath_data,
                        )
            else:
                WARNING.logger.warning("检查到数据库开关为关闭状态，请确认配置")

    def dependent_handler(
            self, _jsonpath: Text, set_value: Text, replace_key: Text,
            jsonpath_dates: Dict, data: Dict, dependent_type: int) -> None:
        """
        通用依赖数据处理方法

        从指定的数据源（响应/请求）中通过 JSONPath 提取值，
        并根据配置决定是写入缓存还是替换到当前用例中。

        Args:
            _jsonpath: JSONPath 表达式
            set_value: 缓存键名（可选）
            replace_key: 替换路径（可选）
            jsonpath_dates: 存储所有替换数据的字典
            data: 数据源（响应 JSON 或请求参数）
            dependent_type: 依赖类型标识（0=response, 1=request）
        """
        # 通过 JSONPath 从数据源中提取值
        jsonpath_data = self.jsonpath_data(data, _jsonpath)

        # 如果定义了缓存键，将值写入缓存
        if set_value is not None:
            if len(jsonpath_data) > 1:
                # 提取到多个值，存入整个列表
                CacheHandler.update_cache(cache_name=set_value, value=jsonpath_data)
            else:
                # 只提取到一个值，直接存入缓存
                CacheHandler.update_cache(cache_name=set_value, value=jsonpath_data[0])

        # 如果定义了替换键，将值加入替换字典
        if replace_key is not None:
            if dependent_type == 0:
                jsonpath_dates[replace_key] = jsonpath_data[0]
            self.url_replace(
                replace_key=replace_key,
                jsonpath_dates=jsonpath_dates,
                jsonpath_data=jsonpath_data
            )

    def is_dependent(self) -> Union[Dict, bool]:
        """
        检查并处理所有接口依赖

        【执行流程】
        1. 判断当前用例是否定义了接口依赖（dependence_case = true）
        2. 遍历所有被依赖的用例
        3. 根据 case_id 判断是 SQL 依赖还是接口依赖
           - case_id = "self": 从前置 SQL 结果中提取
           - 其他值: 从被依赖接口的响应中提取
        4. 根据 dependent_type 决定从响应还是请求中提取数据
        5. 将所有替换数据收集到 jsonpath_dates 字典中

        Returns:
            Dict: 所有需要替换的数据（键为替换路径，值为新值）
            bool: 如果没有依赖，返回 False

        Raises:
            ValueNotFoundError: 如果依赖数据中缺少必要参数

        Java 类比：
        public Map<String, Object> resolveDependencies() {
            if (!yamlCase.isDependenceCase()) {
                return false;
            }
            Map<String, Object> dates = new HashMap<>();
            for (DependentCaseData depData : yamlCase.getDependenceCaseData()) {
                // Resolve each dependency
            }
            return dates;
        }
        """
        # 获取用例中的 dependence_case 值，判断是否需要执行依赖
        _dependent_type = self.__yaml_case.dependence_case
        # 获取依赖用例数据
        _dependence_case_dates = self.__yaml_case.dependence_case_data
        _setup_sql = self.__yaml_case.setup_sql

        # 判断是否有依赖
        if _dependent_type is True:
            # 读取依赖相关的用例数据
            jsonpath_dates = {}
            # 循环所有需要依赖的数据
            try:
                for dependence_case_data in _dependence_case_dates:
                    _case_id = dependence_case_data.case_id
                    # 判断依赖数据为 SQL，case_id 需要写成 "self"
                    # （从当前用例的前置 SQL 结果中提取数据）
                    if _case_id == 'self':
                        self._dependent_type_for_sql(
                            setup_sql=_setup_sql,
                            dependence_case_data=dependence_case_data,
                            jsonpath_dates=jsonpath_dates)
                    else:
                        # 从缓存中获取被依赖用例的数据
                        re_data = regular(str(self.get_cache(_case_id)))
                        re_data = ast.literal_eval(cache_regular(str(re_data)))
                        # 对被依赖用例发起请求
                        res = RequestControl(re_data).http_request()

                        if dependence_case_data.dependent_data is not None:
                            dependent_data = dependence_case_data.dependent_data
                            for i in dependent_data:
                                _case_id = dependence_case_data.case_id
                                _jsonpath = i.jsonpath
                                _request_data = self.__yaml_case.data
                                _replace_key = self.replace_key(i)
                                _set_value = self.set_cache_value(i)

                                # 判断依赖数据类型：依赖 response 中的数据
                                if i.dependent_type == DependentType.RESPONSE.value:
                                    self.dependent_handler(
                                        data=json.loads(res.response_data),
                                        _jsonpath=_jsonpath,
                                        set_value=_set_value,
                                        replace_key=_replace_key,
                                        jsonpath_dates=jsonpath_dates,
                                        dependent_type=0
                                    )

                                # 判断依赖数据类型：依赖 request 中的数据
                                elif i.dependent_type == DependentType.REQUEST.value:
                                    self.dependent_handler(
                                        data=res.body,
                                        _jsonpath=_jsonpath,
                                        set_value=_set_value,
                                        replace_key=_replace_key,
                                        jsonpath_dates=jsonpath_dates,
                                        dependent_type=1
                                    )

                                else:
                                    raise ValueError(
                                        "依赖的dependent_type不正确，只支持request、response、sql依赖\n"
                                        f"当前填写内容: {i.dependent_type}"
                                    )
                return jsonpath_dates
            except KeyError as exc:
                raise ValueNotFoundError(
                    f"dependence_case_data依赖用例中，未找到 {exc} 参数，请检查是否填写"
                    f"如已填写，请检查是否存在yaml缩进问题"
                ) from exc
            except TypeError as exc:
                raise ValueNotFoundError(
                    "dependence_case_data下的所有内容均不能为空！"
                    "请检查相关数据是否填写，如已填写，请检查缩进问题"
                ) from exc
        else:
            return False

    def get_dependent_data(self) -> None:
        """
        执行 JSONPath 数据替换

        将 is_dependent() 方法收集到的所有替换数据，
        通过 exec() 动态赋值到当前用例对象的对应字段中。

        原理：
        - jsonpath_replace 函数根据替换路径生成 Python 赋值语句
        - exec() 执行这些赋值语句，实现动态字段赋值

        示例：
        替换路径：$.data.id
        生成代码：__yaml_case.data['id'] = 123
        exec 执行后，__yaml_case.data['id'] 的值变为 123

        Java 类比：
        public void applyDependentData(Map<String, Object> replacements) {
            for (Map.Entry<String, Object> entry : replacements.entrySet()) {
                JsonPath.put(yamlCase, entry.getKey(), entry.getValue());
            }
        }
        """
        _dependent_data = DependentCase(self.__yaml_case).is_dependent()
        _new_data = None
        # 判断有依赖
        if _dependent_data is not None and _dependent_data is not False:
            for key, value in _dependent_data.items():
                # 通过 JSONPath 判断出需要替换数据的位置
                _change_data = key.split(".")
                # jsonpath 数据解析
                # jsonpath_replace 生成 Python 赋值语句的前半部分
                yaml_case = self.__yaml_case
                _new_data = jsonpath_replace(change_data=_change_data, key_name='yaml_case')
                # 拼接赋值语句的后半部分（= 值）
                _new_data += ' = ' + str(value)
                # 动态执行赋值语句
                exec(_new_data)
