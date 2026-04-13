#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/3/28 12:52
# @Author : 余少琪
# @Description: HTTP 请求执行器 —— 整个框架的核心引擎
#
# 【文件作用】
# RequestControl 类负责将 YAML 中定义的测试用例转换为真实的 HTTP 请求，
# 并封装响应数据。它支持多种请求类型（JSON/PARAMS/DATA/FILE/EXPORT/NONE），
# 处理接口依赖、鉴权注入、缓存管理、SQL 查询等功能。
#
# 【核心流程】
# 1. 接收 YAML 用例数据 -> 转为 TestCase 对象
# 2. 处理接口依赖（如果有）
# 3. 注入鉴权 token
# 4. 根据 requestType 分发到对应的请求方法
# 5. 发送 HTTP 请求
# 6. 封装响应数据为 ResponseData 对象
# 7. 写入 Allure 报告步骤
# 8. 将响应数据存入缓存（如果有配置）
#
# 【Java 对比说明】
# - requests.request() 类似于 Java 的 HttpClient 或 RestTemplate
# - MultipartEncoder 类似于 Java 的 MultipartEntityBuilder
# - ast.literal_eval 类似于 Java 的 ObjectMapper.readValue()
import ast
import os
import random
import time
import urllib
from typing import Tuple, Dict, Union, Text
import requests
import urllib3
from requests_toolbelt import MultipartEncoder
from common.setting import ensure_path_sep
from utils.other_tools.models import RequestType
from utils.logging_tool.log_decorator import log_decorator
from utils.mysql_tool.mysql_control import AssertExecution
from utils.logging_tool.run_time_decorator import execution_duration
from utils.other_tools.allure_data.allure_tools import allure_step, allure_step_no, allure_attach
from utils.read_files_tools.regular_control import cache_regular
from utils.requests_tool.set_current_request_cache import SetCurrentRequestCache
from utils.other_tools.models import TestCase, ResponseData
from utils.cache_process.cache_control import CacheHandler, Cache
from utils import config
# from utils.requests_tool.encryption_algorithm_control import encryption

# 禁用 urllib3 的不安全请求警告（verify=False 时的警告）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class RequestControl:
    """
    HTTP 请求控制器

    核心职责：
    - 将 YAML 用例数据转为 HTTP 请求
    - 支持多种请求体类型（JSON/PARAMS/DATA/FILE/EXPORT）
    - 文件上传处理（multipart/form-data）
    - 响应数据封装和缓存管理

    Java 类比：
    public class RequestControl {
        private TestCase yamlCase;

        public RequestControl(Map<String, Object> yamlCase) {
            this.yamlCase = new TestCase(yamlCase);
        }

        public ResponseData httpRequest(boolean dependentSwitch) { ... }
    }
    """

    def __init__(self, yaml_case):
        """
        初始化请求控制器

        Args:
            yaml_case: YAML 解析后的用例数据（字典格式）
        """
        # 将字典转为强类型的 TestCase 对象，便于后续属性访问
        self.__yaml_case = TestCase(**yaml_case)

    def file_data_exit(self, file_data) -> None:
        """
        文件上传辅助方法：判断并合并额外的 data 参数

        场景：有些接口既要上传文件，又要传递额外的表单参数。
        这个方法将 YAML 中 data.data 下的参数合并到 file_data 中。

        Args:
            file_data: 已构建的文件参数字典

        Java 类比：
        private void mergeFormData(Map<String, Object> fileData) {
            Map<String, Object> data = yamlCase.getData();
            for (Map.Entry<String, Object> entry : data.get("data").entrySet()) {
                fileData.put(entry.getKey(), entry.getValue());
            }
        }
        """
        # 兼容既要上传文件，又要上传其他类型参数的场景
        try:
            _data = self.__yaml_case.data
            for key, value in ast.literal_eval(cache_regular(str(_data)))['data'].items():
                file_data[key] = value
        except KeyError:
            ...  # Python 的 pass 简写，表示什么都不做

    @classmethod
    def multipart_data(cls, file_data: Dict):
        """
        处理文件上传数据，构建 multipart/form-data 格式的请求体

        使用 requests_toolbelt 的 MultipartEncoder 将文件数据
        编码为 multipart 格式，同时生成随机的 boundary 分隔符。

        Args:
            file_data: 文件数据字典，格式为 {字段名: (文件名, 文件内容, MIME类型)}

        Returns:
            MultipartEncoder: 编码后的 multipart 对象

        Java 类比：
        MultipartEntityBuilder.create()
            .addBinaryBody("file", fileContent)
            .setBoundary("----" + randomLong)
            .build()
        """
        multipart = MultipartEncoder(
            fields=file_data,  # 字典格式
            # 生成随机 boundary（28-29位的数字）
            boundary='-----------------------------' + str(random.randint(int(1e28), int(1e29 - 1)))
        )
        return multipart

    @classmethod
    def check_headers_str_null(cls, headers: Dict) -> Dict:
        """
        检查并处理请求头：确保所有 header 值都是字符串类型

        兼容性处理：用户可能在 YAML 中将 header 值写成 int 类型，
        但 HTTP 协议要求 header 值必须是字符串。

        Args:
            headers: 原始请求头字典

        Returns:
            Dict: 处理后的请求头字典（所有值都转为 str）

        Java 类比：
        private Map<String, String> normalizeHeaders(Map<String, Object> headers) {
            Map<String, String> result = new HashMap<>();
            for (Map.Entry<String, Object> entry : headers.entrySet()) {
                result.put(entry.getKey(), String.valueOf(entry.getValue()));
            }
            return result;
        }
        """
        # cache_regular 解析动态表达式，ast.literal_eval 将字符串转为 Python 对象
        headers = ast.literal_eval(cache_regular(str(headers)))
        if headers is None:
            headers = {"headers": None}
        else:
            for key, value in headers.items():
                if not isinstance(value, str):
                    headers[key] = str(value)
        return headers

    @classmethod
    def multipart_in_headers(cls, request_data: Dict, header: Dict):
        """
        处理 Content-Type 为 multipart/form-data 的请求

        当 header 中声明了 multipart/form-data 时：
        1. 将请求数据转为 MultipartEncoder 格式
        2. 将 header 中的 Content-Type 更新为正确的 boundary 值
        3. 将所有非字符串类型的值转为字符串

        Args:
            request_data: 请求体数据
            header: 请求头

        Returns:
            tuple: (处理后的请求体, 处理后的请求头)

        Java 类比：
        private Tuple<RequestBody, HttpHeaders> handleMultipart(
            Map<String, Object> data, HttpHeaders headers) { ... }
        """
        header = ast.literal_eval(cache_regular(str(header)))
        request_data = ast.literal_eval(cache_regular(str(request_data)))

        if header is None:
            header = {"headers": None}
        else:
            # 将 header 中的 int 值转换成 str
            for key, value in header.items():
                if not isinstance(value, str):
                    header[key] = str(value)
            # 判断 Content-Type 是否为 multipart/form-data
            if "multipart/form-data" in str(header.values()):
                # 判断请求参数不为空，并且参数是字典类型
                if request_data and isinstance(request_data, dict):
                    # 当 Content-Type 为 "multipart/form-data" 时，需要将数据类型转换成 str
                    for key, value in request_data.items():
                        if not isinstance(value, str):
                            request_data[key] = str(value)

                    request_data = MultipartEncoder(request_data)
                    header['Content-Type'] = request_data.content_type

        return request_data, header

    def file_prams_exit(self) -> Dict:
        """
        获取文件上传接口的 URL 查询参数

        有些文件上传接口需要在 URL 上附带额外参数（如 ?type=image），
        这个方法从 YAML 的 data.params 中提取这些参数。

        Returns:
            Dict: URL 查询参数字典，如果不存在则返回 None
        """
        try:
            params = self.__yaml_case.data['params']
        except KeyError:
            params = None
        return params

    @classmethod
    def text_encode(cls, text: Text) -> Text:
        """
        Unicode 解码

        Args:
            text: 需要解码的文本

        Returns:
            str: 解码后的文本
        """
        return text.encode("utf-8").decode("utf-8")

    @classmethod
    def response_elapsed_total_seconds(cls, res) -> float:
        """
        获取接口响应时长（毫秒）

        Args:
            res: requests 响应对象

        Returns:
            float: 响应时长（毫秒），保留两位小数；如果获取失败返回 0.00
        """
        try:
            # res.elapsed.total_seconds() 返回秒数，* 1000 转为毫秒
            return round(res.elapsed.total_seconds() * 1000, 2)
        except AttributeError:
            return 0.00

    def upload_file(self) -> Tuple:
        """
        处理文件上传请求

        【执行流程】
        1. 从 YAML 的 data.file 中读取文件列表
        2. 将每个文件路径转为绝对路径并打开
        3. 构建 MultipartEncoder 对象
        4. 在 Allure 报告中附加文件预览

        Returns:
            tuple: (MultipartEncoder 请求体, URL 查询参数, TestCase 用例数据)

        Java 类比：
        private Tuple<MultipartEntity, Map<String, String>, TestCase> buildUploadRequest() { ... }
        """
        # 处理上传多个文件的情况
        _files = []
        file_data = {}
        # 兼容又要上传文件，又要上传其他类型参数
        self.file_data_exit(file_data)
        _data = self.__yaml_case.data
        # 遍历 data.file 中的每个文件
        for key, value in ast.literal_eval(cache_regular(str(_data)))['file'].items():
            # 构建文件的绝对路径
            file_path = ensure_path_sep("\\Files\\" + value)
            # 打开文件并添加到 file_data
            # (文件名, 文件二进制流, MIME类型)
            file_data[key] = (value, open(file_path, 'rb'), 'application/octet-stream')
            _files.append(file_data)
            # 在 Allure 报告中展示该附件
            allure_attach(source=file_path, name=value, extension=value)
        # 构建 multipart 请求体
        multipart = self.multipart_data(file_data)
        # 更新 header 中的 Content-Type
        self.__yaml_case.headers['Content-Type'] = multipart.content_type
        # 获取 URL 查询参数
        params_data = ast.literal_eval(cache_regular(str(self.file_prams_exit())))
        return multipart, params_data, self.__yaml_case

    def request_type_for_json(self, headers: Dict, method: Text, **kwargs):
        """
        发送 JSON 格式的请求（Content-Type: application/json）

        Args:
            headers: 请求头
            method: HTTP 方法（GET/POST/PUT/DELETE）
            **kwargs: 其他请求参数

        Returns:
            Response: requests 响应对象
        """
        _headers = self.check_headers_str_null(headers)
        _data = self.__yaml_case.data
        _url = self.__yaml_case.url
        res = requests.request(
            method=method,
            url=cache_regular(str(_url)),
            # json= 参数会自动将字典序列化为 JSON 字符串并设置 Content-Type
            json=ast.literal_eval(cache_regular(str(_data))),
            data={},
            headers=_headers,
            verify=False,  # 不验证 SSL 证书
            params=None,
            **kwargs
        )
        return res

    def request_type_for_none(self, headers: Dict, method: Text, **kwargs) -> object:
        """
        发送无请求体的请求（如纯 GET 请求，没有 body）

        Args:
            headers: 请求头
            method: HTTP 方法
            **kwargs: 其他请求参数

        Returns:
            Response: requests 响应对象
        """
        _headers = self.check_headers_str_null(headers)
        _url = self.__yaml_case.url
        res = requests.request(
            method=method,
            url=cache_regular(_url),
            data=None,
            headers=_headers,
            verify=False,
            params=None,
            **kwargs
        )
        return res

    def request_type_for_params(self, headers: Dict, method: Text, **kwargs):
        """
        发送 URL 查询参数格式的请求

        将 YAML 中 data 下的键值对拼接为 URL 查询字符串（?key=value&key2=value2）

        示例：
        data:
          page: 1
          size: 10
        -> URL: /api/users?page=1&size=10

        Args:
            headers: 请求头
            method: HTTP 方法
            **kwargs: 其他请求参数

        Returns:
            Response: requests 响应对象
        """
        _data = self.__yaml_case.data
        url = self.__yaml_case.url
        if _data is not None:
            # 使用 URL 拼接的方式传参
            params_data = "?"
            for key, value in _data.items():
                if value is None or value == '':
                    # 值为空时，只添加 key（如 ?key&）
                    params_data += (key + "&")
                else:
                    # 值不为空时，添加 key=value
                    params_data += (key + "=" + str(value) + "&")
            # 去掉最后的 & 符号
            url = self.__yaml_case.url + params_data[:-1]
        _headers = self.check_headers_str_null(headers)
        res = requests.request(
            method=method,
            url=cache_regular(url),
            headers=_headers,
            verify=False,
            data={},
            params=None,
            **kwargs)
        return res

    def request_type_for_file(self, method: Text, headers, **kwargs):
        """
        发送文件上传请求（multipart/form-data）

        调用 upload_file() 方法构建文件请求体

        Args:
            method: HTTP 方法
            headers: 请求头
            **kwargs: 其他请求参数

        Returns:
            Response: requests 响应对象
        """
        multipart = self.upload_file()
        yaml_data = multipart[2]
        _headers = multipart[2].headers
        _headers = self.check_headers_str_null(_headers)
        res = requests.request(
            method=method,
            url=cache_regular(yaml_data.url),
            data=multipart[0],      # multipart 请求体
            params=multipart[1],    # URL 查询参数
            headers=ast.literal_eval(cache_regular(str(_headers))),
            verify=False,
            **kwargs
        )
        return res

    def request_type_for_data(self, headers: Dict, method: Text, **kwargs):
        """
        发送表单格式的请求（Content-Type: application/x-www-form-urlencoded）

        如果 header 中声明了 multipart/form-data，则自动转为 multipart 格式

        Args:
            headers: 请求头
            method: HTTP 方法
            **kwargs: 其他请求参数

        Returns:
            Response: requests 响应对象
        """
        data = self.__yaml_case.data
        _data, _headers = self.multipart_in_headers(
            ast.literal_eval(cache_regular(str(data))),
            headers
        )
        _url = self.__yaml_case.url
        res = requests.request(
            method=method,
            url=cache_regular(_url),
            data=_data,
            headers=_headers,
            verify=False,
            **kwargs)

        return res

    @classmethod
    def get_export_api_filename(cls, res):
        """
        从导出接口的响应头中提取文件名

        导出接口通常在 Content-Disposition 头中返回文件名：
        Content-Disposition: attachment; filename="report.xlsx"

        Args:
            res: requests 响应对象

        Returns:
            str: 提取并 URL 解码后的文件名

        Java 类比：
        private String extractFilename(HttpResponse response) {
            String contentDisposition = response.getHeader("Content-Disposition");
            String filename = contentDisposition.split("=")[1];
            return URLDecoder.decode(filename, "UTF-8");
        }
        """
        content_disposition = res.headers.get('content-disposition')
        filename_code = content_disposition.split("=")[-1]  # 分隔字符串，提取文件名
        filename = urllib.parse.unquote(filename_code)  # URL 解码
        return filename

    def request_type_for_export(self, headers: Dict, method: Text, **kwargs):
        """
        发送导出文件请求，并将响应保存为本地文件

        与普通请求不同的是，这个方法会将响应体写入到 Files/ 目录下

        Args:
            headers: 请求头
            method: HTTP 方法
            **kwargs: 其他请求参数

        Returns:
            Response: requests 响应对象
        """
        _headers = self.check_headers_str_null(headers)
        _data = self.__yaml_case.data
        _url = self.__yaml_case.url
        res = requests.request(
            method=method,
            url=cache_regular(_url),
            json=ast.literal_eval(cache_regular(str(_data))),
            headers=_headers,
            verify=False,
            stream=False,
            data={},
            **kwargs)
        # 拼接文件保存路径
        filepath = os.path.join(ensure_path_sep("\\Files\\"), self.get_export_api_filename(res))
        if res.status_code == 200:
            if res.text:  # 判断文件内容是否为空
                with open(filepath, 'wb') as file:
                    # iter_content 循环读取响应流，chunk_size=1 表示每次读取 1 字节
                    for chunk in res.iter_content(chunk_size=1):
                        file.write(chunk)
            else:
                print("文件为空")

        return res

    @classmethod
    def _request_body_handler(cls, data: Dict, request_type: Text) -> Union[None, Dict]:
        """
        处理请求体：用于日志展示时判断是否需要打印请求体

        当请求类型为 PARAMS 时，参数在 URL 中，不需要打印 body。

        Args:
            data: 请求体数据
            request_type: 请求类型

        Returns:
            None 或 Dict: PARAMS 类型返回 None，其他类型返回 data
        """
        if request_type.upper() == 'PARAMS':
            return None
        else:
            return data

    @classmethod
    def _sql_data_handler(cls, sql_data, res):
        """
        处理前置 SQL 查询结果

        如果数据库开关开启且用例中定义了 SQL，则执行 SQL 查询
        并将查询结果与响应数据一起用于后续断言。

        Args:
            sql_data: SQL 查询语句列表
            res: HTTP 响应对象

        Returns:
            Dict: SQL 查询结果或 {"sql": None}
        """
        # 判断数据库开关，开启状态，则返回对应的数据
        if config.mysql_db.switch and sql_data is not None:
            sql_data = AssertExecution().assert_execution(
                sql=sql_data,
                resp=res.json()
            )
        else:
            sql_data = {"sql": None}
        return sql_data

    def _check_params(self, res, yaml_data: "TestCase") -> "ResponseData":
        """
        封装响应数据为 ResponseData 对象

        这个方法将 HTTP 响应和原始用例数据整合为一个完整的 ResponseData 对象，
        供后续的断言、日志和报告使用。

        Args:
            res: HTTP 响应对象
            yaml_data: 原始 YAML 用例数据（TestCase 对象）

        Returns:
            ResponseData: 封装后的响应数据对象
        """
        data = ast.literal_eval(cache_regular(str(yaml_data.data)))
        _data = {
            "url": res.url,
            "is_run": yaml_data.is_run,
            "detail": yaml_data.detail,
            "response_data": res.text,
            # 这个用于日志专用，判断如果是 GET 请求，直接打印 URL
            "request_body": self._request_body_handler(
                data, yaml_data.requestType
            ),
            "method": res.request.method,
            "sql_data": self._sql_data_handler(
                sql_data=ast.literal_eval(cache_regular(str(yaml_data.sql))), res=res
            ),
            "yaml_data": yaml_data,
            "headers": res.request.headers,
            "cookie": res.cookies,
            "assert_data": yaml_data.assert_data,
            "res_time": self.response_elapsed_total_seconds(res),
            "status_code": res.status_code,
            "teardown": yaml_data.teardown,
            "teardown_sql": yaml_data.teardown_sql,
            "body": data
        }
        return ResponseData(**_data)

    @classmethod
    def api_allure_step(cls, *, url: Text, headers: Text, method: Text,
                        data: Text, assert_data: Text, res_time: Text,
                        res: Text) -> None:
        """
        在 Allure 报告中记录请求的详细信息

        这些数据会在 Allure HTML 报告中以步骤的形式展示，
        方便查看测试报告时了解每个接口的请求和响应。

        Args:
            url: 请求 URL
            headers: 请求头
            method: HTTP 方法
            data: 请求体
            assert_data: 预期断言数据
            res_time: 响应耗时
            res: 响应结果
        """
        allure_step_no(f"请求URL: {url}")
        allure_step_no(f"请求方式: {method}")
        allure_step("请求头: ", headers)
        allure_step("请求数据: ", data)
        allure_step("预期数据: ", assert_data)
        _res_time = res_time
        allure_step_no(f"响应耗时(ms): {str(_res_time)}")
        allure_step("响应结果: ", res)

    # ====== 装饰器说明 ======
    # @log_decorator(True): 记录请求/响应日志到日志文件
    # @execution_duration(3000): 如果请求耗时超过 3000ms 则告警
    # @encryption("md5"): 已废弃的加密装饰器
    @log_decorator(True)
    @execution_duration(3000)
    # @encryption("md5")
    def http_request(self, dependent_switch=True, **kwargs):
        """
        HTTP 请求主入口方法

        【执行流程】
        1. 判断用例是否执行（is_run 字段）
        2. 处理接口依赖数据（如果 dependent_switch=True）
        3. 注入鉴权 token（如果缓存中存在 auth_token）
        4. 根据 requestType 分发到对应的请求方法
        5. 等待指定时间（如果配置了 sleep）
        6. 封装响应数据
        7. 写入 Allure 报告
        8. 将响应数据存入缓存（如果配置了 current_request_set_cache）

        Args:
            dependent_switch: 是否处理接口依赖（默认 True）
                             后置请求中传 False 避免循环依赖
            **kwargs: 其他请求参数

        Returns:
            ResponseData: 封装后的响应数据对象；如果用例不执行则返回 None

        Java 类比：
        public ResponseData executeHttpRequest(boolean dependentSwitch, HttpRequestOptions... options) {
            // 1. Check if should run
            // 2. Resolve dependencies
            // 3. Inject auth token
            // 4. Dispatch by request type
            // 5. Execute request
            // 6. Wrap response
            // 7. Log to report
            // 8. Cache response data
        }
        """
        # 延迟导入，避免循环依赖
        from utils.requests_tool.dependent_case import DependentCase

        # 请求类型分发映射：RequestType -> 对应的请求方法
        requests_type_mapping = {
            RequestType.JSON.value: self.request_type_for_json,
            RequestType.NONE.value: self.request_type_for_none,
            RequestType.PARAMS.value: self.request_type_for_params,
            RequestType.FILE.value: self.request_type_for_file,
            RequestType.DATA.value: self.request_type_for_data,
            RequestType.EXPORT.value: self.request_type_for_export
        }

        # 解析 is_run 字段，判断是否执行该用例
        is_run = ast.literal_eval(cache_regular(str(self.__yaml_case.is_run)))

        # 判断用例是否执行（True 或 None 都表示执行）
        if is_run is True or is_run is None:
            # ====== 第一步：处理接口依赖 ======
            if dependent_switch is True:
                DependentCase(self.__yaml_case).get_dependent_data()

            # ====== 第二步：注入鉴权 token ======
            # 从缓存中读取 auth_token，如果存在则添加到 headers 中
            try:
                auth_token = CacheHandler.get_cache('auth_token')
                if auth_token:
                    headers = self.__yaml_case.headers or {}
                    headers['Authorization'] = auth_token
                    self.__yaml_case.headers = headers
            except Exception:
                pass  # 如果缓存中没有 token，忽略异常

            # ====== 第三步：根据请求类型发送请求 ======
            res = requests_type_mapping.get(self.__yaml_case.requestType)(
                headers=self.__yaml_case.headers,
                method=self.__yaml_case.method,
                **kwargs
            )

            # ====== 第四步：等待指定时间 ======
            if self.__yaml_case.sleep is not None:
                time.sleep(self.__yaml_case.sleep)

            # ====== 第五步：封装响应数据 ======
            _res_data = self._check_params(
                res=res,
                yaml_data=self.__yaml_case)

            # ====== 第六步：写入 Allure 报告 ======
            self.api_allure_step(
                url=_res_data.url,
                headers=str(_res_data.headers),
                method=_res_data.method,
                data=str(_res_data.body),
                assert_data=str(_res_data.assert_data),
                res_time=str(_res_data.res_time),
                res=_res_data.response_data
            )

            # ====== 第七步：将当前请求数据存入缓存 ======
            SetCurrentRequestCache(
                current_request_set_cache=self.__yaml_case.current_request_set_cache,
                request_data=self.__yaml_case.data,
                response_data=res
            ).set_caches_main()

            return _res_data
