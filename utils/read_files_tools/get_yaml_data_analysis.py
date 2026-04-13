#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/3/28 10:56
# @Author : 余少琪
# @Description: YAML 用例数据解析器
#
# 【文件作用】
# 这是框架中非常重要的一个文件。
# CaseData 类负责将 YAML 文件中原始的测试用例数据，
# 解析、校验并转换为框架内部使用的标准格式。
#
# 每个 YAML 用例文件包含：
# - case_common: 公共配置（allure 标签等）
# - case_id_001: 具体的测试用例
# - case_id_002: 另一个测试用例
#
# CaseData 负责遍历每个用例，提取所有必要的字段，
# 并将它们组装成 TestCase 对象需要的字典格式。
#
# 【Java 对比说明】
# 类似于 Java 中的 DTO 转换器：
# public TestCaseDTO convertToDTO(Map<String, Object> yamlData) {
#     TestCaseDTO dto = new TestCaseDTO();
#     dto.setMethod(getMethod(yamlData));
#     dto.setUrl(getUrl(yamlData));
#     dto.setAssertData(getAssert(yamlData));
#     // ...
#     return dto;
# }
from typing import Union, Text, Dict, List
from utils.read_files_tools.yaml_control import GetYamlData
from utils.other_tools.models import TestCase
from utils.other_tools.exceptions import ValueNotFoundError
from utils.cache_process.cache_control import CacheHandler
from utils import config
import os


class CaseData:
    """
    YAML 用例数据解析器

    核心职责：
    - 读取 YAML 文件并遍历所有用例
    - 提取每个用例的所有字段（url、method、headers、data、assert 等）
    - 校验字段值的合法性
    - 将数据转为 TestCase 模型对象

    Java 类比：
    public class CaseData {
        private String filePath;

        public List<TestCase> caseProcess(Boolean caseIdSwitch) {
            Map<String, Object> dates = getYamlData(filePath);
            List<TestCase> cases = new ArrayList<>();
            for (Map.Entry<String, Object> entry : dates.entrySet()) {
                if (!"case_common".equals(entry.getKey())) {
                    TestCase tc = new TestCase();
                    tc.setMethod(getCaseMethod(entry.getKey(), entry.getValue()));
                    tc.setUrl(getCaseHost(entry.getKey(), entry.getValue()));
                    // ...
                    cases.add(tc);
                }
            }
            return cases;
        }
    }
    """

    def __init__(self, file_path):
        """
        初始化用例数据解析器

        Args:
            file_path: YAML 用例文件的绝对路径
        """
        self.file_path = file_path

    def __new__(cls, file_path):
        """
        重写 __new__ 方法：在对象创建前校验文件是否存在

        如果文件不存在，直接抛出异常，不创建对象实例。
        类似于 Java 的工厂方法中先校验参数再创建对象。
        """
        if os.path.exists(file_path) is True:
            return object.__new__(cls)
        else:
            raise FileNotFoundError("用例地址未找到")

    def case_process(self, case_id_switch: Union[None, bool] = None):
        """
        数据清洗主方法 —— 解析 YAML 文件中的所有测试用例

        【执行流程】
        1. 读取 YAML 文件数据
        2. 遍历每个用例（跳过 case_common 公共配置）
        3. 调用各个 get_* 方法提取用例字段
        4. 组装为字典并转为 TestCase 对象
        5. 返回所有用例的列表

        Args:
            case_id_switch: 是否在结果中包含 case_id 键
                           True: 返回 [{case_id: TestCase字典}, ...]
                           False/None: 返回 [TestCase字典, ...]

        Returns:
            list: 所有测试用例的数据列表
        """
        dates = GetYamlData(self.file_path).get_yaml_data()
        case_lists = []
        for key, values in dates.items():
            # 公共配置中的数据，与用例数据不同，需要单独处理
            if key != 'case_common':
                case_date = {
                    'method': self.get_case_method(case_id=key, case_data=values),
                    'is_run': self.get_is_run(key, values),
                    'url': self.get_case_host(case_id=key, case_data=values),
                    'detail': self.get_case_detail(case_id=key, case_data=values),
                    'headers': self.get_headers(case_id=key, case_data=values),
                    'requestType': self.get_request_type(key, values),
                    'data': self.get_case_dates(key, values),
                    'dependence_case': self.get_dependence_case(key, values),
                    'dependence_case_data': self.get_dependence_case_data(key, values),
                    "current_request_set_cache": self.get_current_request_set_cache(values),
                    "sql": self.get_sql(key, values),
                    "assert_data": self.get_assert(key, values),
                    "setup_sql": self.setup_sql(values),
                    "teardown": self.tear_down(values),
                    "teardown_sql": self.teardown_sql(values),
                    "sleep": self.time_sleep(values),
                }
                if case_id_switch is True:
                    case_lists.append({key: TestCase(**case_date).dict()})
                else:
                    # 正则处理：如果用例中有需要读取缓存中的数据，则优先读取缓存
                    case_lists.append(TestCase(**case_date).dict())
        return case_lists

    def get_case_host(self, case_id: Text, case_data: Dict) -> Text:
        """
        获取用例的完整 URL（host + url）

        将 YAML 中的 host 和 url 拼接为完整的请求地址。

        Args:
            case_id: 用例 ID
            case_data: 用例数据字典

        Returns:
            str: 完整的请求 URL（如 "https://api.example.com/api/v1/user/login"）

        Raises:
            ValueNotFoundError: 如果 url 或 host 为空
        """
        try:
            _url = case_data['url']
            _host = case_data['host']
            if _url is None or _host is None:
                raise ValueNotFoundError(
                    f"用例中的 url 或者 host 不能为空！\n "
                    f"用例ID: {case_id} \n "
                    f"用例路径: {self.file_path}"
                )
            return _host + _url
        except KeyError as exc:
            raise ValueNotFoundError(
                self.raise_value_null_error(data_name="url 或 host", case_id=case_id)
            ) from exc

    def get_case_method(self, case_id: Text, case_data: Dict) -> Text:
        """
        获取用例的请求方法（GET/POST/PUT/DELETE 等）

        校验请求方法是否合法，只支持常见的 HTTP 方法。

        Args:
            case_id: 用例 ID
            case_data: 用例数据字典

        Returns:
            str: 大写的 HTTP 方法（如 "POST"）

        Raises:
            ValueNotFoundError: 如果 method 未填写或不合法
        """
        try:
            _case_method = case_data['method']
            _request_method = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTION']
            if _case_method.upper() not in _request_method:
                raise ValueNotFoundError(
                    f"method 目前只支持 {_request_method} 请求方式，如需新增请联系管理员. "
                    f"{self.raise_value_error(data_name='请求方式', case_id=case_id, detail=_case_method)}"
                )
            return _case_method.upper()

        except AttributeError as exc:
            raise ValueNotFoundError(
                f"method 目前只支持 {['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTION']} 请求方式，"
                f"如需新增请联系管理员！ "
                f"{self.raise_value_error(data_name='请求方式', case_id=case_id, detail=case_data['method'])}"
            ) from exc
        except KeyError as exc:
            raise ValueNotFoundError(
                self.raise_value_null_error(data_name="method", case_id=case_id)
            ) from exc

    @classmethod
    def get_current_request_set_cache(cls, case_data: Dict) -> Dict:
        """
        获取当前请求的缓存设置配置

        Args:
            case_data: 用例数据字典

        Returns:
            Dict: 缓存设置配置；如果未定义则返回 None
        """
        try:
            return case_data['current_request_set_cache']
        except KeyError:
            ...  # Python 的 pass 简写

    def get_case_detail(self, case_id: Text, case_data: Dict) -> Text:
        """
        获取用例描述

        Args:
            case_id: 用例 ID
            case_data: 用例数据字典

        Returns:
            str: 用例描述（如 "用户登录接口测试"）

        Raises:
            ValueNotFoundError: 如果 detail 未填写
        """
        try:
            return case_data['detail']
        except KeyError as exc:
            raise ValueNotFoundError(
                self.raise_value_null_error(case_id=case_id, data_name="detail")
            ) from exc

    def get_headers(self, case_id: Text, case_data: Dict) -> Dict:
        """
        获取用例的请求头信息

        Args:
            case_id: 用例 ID
            case_data: 用例数据字典

        Returns:
            Dict: 请求头字典（如 {"Content-Type": "application/json"}）

        Raises:
            ValueNotFoundError: 如果 headers 未定义
        """
        try:
            _header = case_data['headers']
            return _header
        except KeyError as exc:
            raise ValueNotFoundError(
                self.raise_value_null_error(case_id=case_id, data_name="headers")
            ) from exc

    def raise_value_error(self, data_name: Text, case_id: Text, detail) -> Text:
        """
        生成用例参数填写不规范的错误提示

        Args:
            data_name: 参数名称（如 "method", "url"）
            case_id: 用例 ID
            detail: 当前填写的内容

        Returns:
            str: 格式化的错误提示信息
        """
        detail = f"用例中的 {data_name} 填写不正确！\n " \
                 f"用例ID: {case_id} \n" \
                 f" 用例路径: {self.file_path}\n" \
                 f"当前填写的内容: {detail}"
        return detail

    def raise_value_null_error(self, data_name: Text, case_id: Text) -> Text:
        """
        生成用例参数为空的错误提示

        Args:
            data_name: 参数名称
            case_id: 用例 ID

        Returns:
            str: 格式化的错误提示信息
        """
        detail = f"用例中未找到 {data_name} 参数， 如已填写，请检查用例缩进是否存在问题" \
                 f"用例ID: {case_id} " \
                 f"用例路径: {self.file_path}"
        return detail

    def get_request_type(self, case_id: Text, case_data: Dict) -> Text:
        """
        获取用例的请求体类型

        支持的值：JSON, PARAMS, FILE, DATA, EXPORT, NONE

        Args:
            case_id: 用例 ID
            case_data: 用例数据字典

        Returns:
            str: 大写的请求类型

        Raises:
            ValueNotFoundError: 如果 requestType 未填写或不合法
        """
        _types = ['JSON', 'PARAMS', 'FILE', 'DATA', "EXPORT", "NONE"]

        try:
            _request_type = str(case_data['requestType'])
            # 判断用户填写的 requestType 是否符合规范
            if _request_type.upper() not in _types:
                raise ValueNotFoundError(
                    self.raise_value_error(
                        data_name='requestType',
                        case_id=case_id,
                        detail=_request_type
                    )
                )
            return _request_type.upper()
        except AttributeError as exc:
            raise ValueNotFoundError(
                self.raise_value_error(
                    data_name='requestType',
                    case_id=case_id,
                    detail=case_data['requestType'])
            ) from exc
        except KeyError as exc:
            raise ValueNotFoundError(
                self.raise_value_null_error(case_id=case_id, data_name="requestType")
            ) from exc

    def get_is_run(self, case_id: Text, case_data: Dict) -> Text:
        """
        获取用例的执行状态

        为 True 或 None 的用例会正常执行，为 False 的用例会跳过。

        Args:
            case_id: 用例 ID
            case_data: 用例数据字典

        Returns:
            str/bool: 执行状态

        Raises:
            ValueNotFoundError: 如果 is_run 未定义
        """
        try:
            return case_data['is_run']
        except KeyError as exc:
            raise ValueNotFoundError(
                self.raise_value_null_error(case_id=case_id, data_name="is_run")
            ) from exc

    def get_dependence_case(self, case_id: Text, case_data: Dict) -> Dict:
        """
        获取用例是否定义了接口依赖

        Args:
            case_id: 用例 ID
            case_data: 用例数据字典

        Returns:
            bool: 是否存在接口依赖

        Raises:
            ValueNotFoundError: 如果 dependence_case 未定义
        """
        try:
            _dependence_case = case_data['dependence_case']
            return _dependence_case
        except KeyError as exc:
            raise ValueNotFoundError(
                self.raise_value_null_error(case_id=case_id, data_name="dependence_case")
            ) from exc

    # TODO 对 dependence_case_data 中的值进行验证
    def get_dependence_case_data(self, case_id: Text, case_data: Dict) -> Union[Dict, None]:
        """
        获取用例的接口依赖数据

        如果用例定义了依赖，则返回依赖数据；否则返回 None。

        Args:
            case_id: 用例 ID
            case_data: 用例数据字典

        Returns:
            Dict/None: 接口依赖数据

        Raises:
            ValueNotFoundError: 如果 dependence_case=true 但 dependence_case_data 为空
        """
        # 判断如果该用例有依赖，则返回依赖数据
        if self.get_dependence_case(case_id=case_id, case_data=case_data):
            try:
                _dependence_case_data = case_data['dependence_case_data']
                # 判断当用例中设置的需要依赖用例，
                # 但是 dependence_case_data 下方没有填写依赖的数据，异常提示
                if _dependence_case_data is None:
                    raise ValueNotFoundError(f"dependence_case_data 依赖数据中缺少依赖相关数据！"
                                             f"如有填写，请检查缩进是否正确"
                                             f"用例ID: {case_id}"
                                             f"用例路径: {self.file_path}")

                return _dependence_case_data
            except KeyError as exc:
                raise ValueNotFoundError(
                    self.raise_value_null_error(case_id=case_id, data_name="dependence_case_data")
                ) from exc
        else:
            return None

    def get_case_dates(self, case_id: Text, case_data: Dict) -> Dict:
        """
        获取用例的请求体数据

        Args:
            case_id: 用例 ID
            case_data: 用例数据字典

        Returns:
            Dict: 请求体数据

        Raises:
            ValueNotFoundError: 如果 data 未定义
        """
        try:
            _dates = case_data['data']
            return _dates

        except KeyError as exc:
            raise ValueNotFoundError(
                self.raise_value_null_error(case_id=case_id, data_name="data")
            ) from exc

    # TODO 对 assert 中的值进行验证
    def get_assert(self, case_id: Text, case_data: Dict):
        """
        获取用例的断言数据

        Args:
            case_id: 用例 ID
            case_data: 用例数据字典

        Returns:
            Dict: 断言数据

        Raises:
            ValueNotFoundError: 如果 assert 未定义或为空
        """
        try:
            _assert = case_data['assert']
            if _assert is None:
                raise self.raise_value_error(data_name="assert", case_id=case_id, detail=_assert)
            return case_data['assert']
        except KeyError as exc:
            raise ValueNotFoundError(
                self.raise_value_null_error(case_id=case_id, data_name="assert")
            ) from exc

    def get_sql(self, case_id: Text, case_data: Dict) -> Union[list, None]:
        """
        获取用例的断言 SQL

        用于数据库断言场景：查询数据库数据与接口响应进行比较。

        Args:
            case_id: 用例 ID
            case_data: 用例数据字典

        Returns:
            list: SQL 语句列表；如果数据库未开启或 SQL 为空则返回 None
        """
        try:
            _sql = case_data['sql']
            # 判断数据库开关为开启状态，并且 sql 不为空
            if config.mysql_db.switch and _sql is None:
                return None
            return case_data['sql']
        except KeyError as exc:
            raise ValueNotFoundError(
                self.raise_value_null_error(case_id=case_id, data_name="sql")
            ) from exc

    @classmethod
    def setup_sql(cls, case_data: Dict) -> Union[list, None]:
        """
        获取前置 SQL

        前置 SQL 用于在用例执行前从数据库中准备测试数据。

        Args:
            case_data: 用例数据字典

        Returns:
            list: 前置 SQL 语句列表；如果未定义则返回 None
        """
        try:
            _setup_sql = case_data['setup_sql']
            return _setup_sql
        except KeyError:
            return None

    @classmethod
    def tear_down(cls, case_data: Dict) -> Union[Dict, None]:
        """
        获取后置请求数据

        后置请求用于在用例执行后进行清理操作（如删除测试数据）。

        Args:
            case_data: 用例数据字典

        Returns:
            Dict: 后置请求数据；如果未定义则返回 None
        """
        try:
            _teardown = case_data['teardown']
            return _teardown
        except KeyError:
            return None

    @classmethod
    def teardown_sql(cls, case_data: Dict) -> Union[list, None]:
        """
        获取后置 SQL

        后置 SQL 用于在用例执行后清理数据库中产生的测试数据（DELETE 语句）。

        Args:
            case_data: 用例数据字典

        Returns:
            list: 后置 SQL 语句列表；如果未定义则返回 None
        """
        try:
            _teardown_sql = case_data['teardown_sql']
            return _teardown_sql
        except KeyError:
            return None

    @classmethod
    def time_sleep(cls, case_data: Dict) -> Union[int, float, None]:
        """
        获取用例的休眠时间

        用于在用例执行前等待一段时间（秒）。

        Args:
            case_data: 用例数据字典

        Returns:
            int/float/None: 休眠时间（秒）；如果未定义则返回 None
        """
        try:
            _sleep_time = case_data['sleep']
            return _sleep_time
        except KeyError:
            return None


class GetTestCase:
    """
    测试用例数据获取器

    核心职责：
    从缓存中读取已经解析好的用例数据。
    """

    @staticmethod
    def case_data(case_id_lists: List):
        """
        从缓存中批量获取用例数据

        Args:
            case_id_lists: 用例 ID 列表

        Returns:
            list: 所有用例的数据列表
        """
        case_lists = []
        for i in case_id_lists:
            _data = CacheHandler.get_cache(i)
            case_lists.append(_data)

        return case_lists


if __name__ == '__main__':
    a = CaseData(r'D:\work_code\pytest-auto-api2\data\Collect\collect_addtool.yaml').case_process()
    print(a)
