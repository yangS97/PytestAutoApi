#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Description: 全局数据模型定义（Pydantic Models）
#
# 本文件定义了整个框架中使用的所有数据结构，类似于 Java 中的 Entity/DTO/POJO 类
#
# 【核心概念说明】
# 1. Enum（枚举）: 类似于 Java 的 enum，用于定义固定值的集合
# 2. @dataclass（数据类）: Python 的轻量级数据容器类，自动生
#    成 __init__、__repr__ 等方法，类似于 Java 的 Record 或 Lombok @Data
# 3. BaseModel（Pydantic 模型）: 用于数据验证和序列化
#    - 自动校验字段类型
#    - 支持可选字段（Optional）
#    - 类似于 Java 中的 Bean Validation（@NotNull, @NotBlank 等）
# 4. @unique 装饰器: 确保枚举值唯一，不允许重复

import types
from enum import Enum, unique
from typing import Text, Dict, Callable, Union, Optional, List, Any
from dataclasses import dataclass
from pydantic import BaseModel, Field


# ==================== 通知相关枚举 ====================

class NotificationType(Enum):
    """
    自动化通知方式枚举

    对应 config.yaml 中的 notification_type 配置项：
    0 = 不发送通知
    1 = 钉钉通知
    2 = 企业微信通知
    3 = 邮件通知
    4 = 飞书通知

    Java 类比：
    public enum NotificationType { DEFAULT(0), DING_TALK(1), WECHAT(2), EMAIL(3), FEI_SHU(4) }
    """
    DEFAULT = 0
    DING_TALK = 1
    WECHAT = 2
    EMAIL = 3
    FEI_SHU = 4


# ==================== 测试指标数据类 ====================

@dataclass
class TestMetrics:
    """
    测试用例执行统计数据

    Attributes:
        passed: 通过的用例数量
        failed: 失败的用例数量
        broken: 异常的用例数量（执行出错，非断言失败）
        skipped: 跳过的用例数量
        total: 总用例数
        pass_rate: 通过率（百分比，如 95.5）
        time: 执行耗时（格式化的时间字符串）

    Java 类比：
    public record TestMetrics(int passed, int failed, int broken, int skipped,
                              int total, double passRate, String time) {}
    """
    passed: int
    failed: int
    broken: int
    skipped: int
    total: int
    pass_rate: float
    time: Text


# ==================== 请求相关枚举 ====================

class RequestType(Enum):
    """
    HTTP 请求体数据类型枚举

    定义请求参数的传递方式：
    - JSON: 以 JSON 格式发送（Content-Type: application/json）
    - PARAMS: 以 URL 查询参数发送（如 ?key=value）
    - DATA: 以表单格式发送（Content-Type: application/x-www-form-urlencoded）
    - FILE: 以文件上传方式发送（multipart/form-data）
    - EXPORT: 导出接口专用
    - NONE: 无请求体（如 GET 请求）

    Java 类比：
    public enum RequestType { JSON, PARAMS, DATA, FILE, EXPORT, NONE }
    """
    JSON = "JSON"
    PARAMS = "PARAMS"
    DATA = "DATA"
    FILE = 'FILE'
    EXPORT = "EXPORT"
    NONE = "NONE"


# ==================== 工具函数 ====================

def load_module_functions(module) -> Dict[Text, Callable]:
    """
    获取指定模块中所有函数的名称和内存地址（函数对象）

    用途：在自定义断言等场景中，通过函数名动态调用函数

    Args:
        module: Python 模块对象

    Returns:
        Dict[str, Callable]: 函数名 -> 函数对象 的映射字典

    Java 类比：
    类似于通过反射获取类中所有 Method 对象：
    Map<String, Method> methods = Arrays.stream(clazz.getDeclaredMethods())
        .collect(Collectors.toMap(Method::getName, m -> m));
    """
    module_functions = {}

    # vars(module) 获取模块的所有属性（包括函数、变量等）
    for name, item in vars(module).items():
        # isinstance(item, types.FunctionType) 判断是否为函数类型
        if isinstance(item, types.FunctionType):
            module_functions[name] = item
    return module_functions


# ==================== 数据依赖相关枚举 ====================

@unique
class DependentType(Enum):
    """
    接口数据依赖类型枚举

    在多接口测试中，后一个接口往往需要前一个接口的返回数据作为入参。
    这个枚举定义了可以从哪些来源获取依赖数据：

    - RESPONSE: 从前一个接口的响应中提取
    - REQUEST: 从前一个接口的请求参数中提取
    - SQL_DATA: 从数据库查询结果中提取
    - CACHE: 从全局缓存中读取

    Java 类比：
    public enum DependentType { RESPONSE, REQUEST, SQL_DATA, CACHE }
    """
    RESPONSE = 'response'
    REQUEST = 'request'
    SQL_DATA = 'sqlData'
    CACHE = "cache"


# ==================== YAML 用例数据模型 ====================

class Assert(BaseModel):
    """
    断言定义模型 —— 定义单个断言的条件和预期值

    字段说明：
    - jsonpath: JSONPath 表达式，用于从响应中提取要断言的字段
      例如: "$.code" 表示提取响应中的 code 字段
    - type: 断言类型（如 "==", ">", "contains" 等）
    - value: 预期值
    - AssertType: 断言分类（如 "json" 表示 JSON 断言，"sql" 表示数据库断言）

    YAML 示例：
    assert:
      - jsonpath: "$.code"
        type: "=="
        value: 200
        AssertType: "json"

    Java 类比：
    public class Assert {
        private String jsonpath;    // JSONPath 表达式
        private String type;        // 断言类型
        private Object value;       // 预期值
        private String assertType;  // 断言分类
    }
    """
    jsonpath: Text
    type: Text
    value: Any
    AssertType: Union[None, Text] = None


class DependentData(BaseModel):
    """
    依赖数据定义模型 —— 定义如何从其他接口提取数据

    字段说明：
    - dependent_type: 依赖类型（RESPONSE/REQUEST/SQL_DATA/CACHE）
    - jsonpath: JSONPath 表达式，用于定位要提取的数据
    - set_cache: 提取后要存储的缓存键名（可选）
    - replace_key: 用于替换的键名（可选）

    Java 类比：
    public class DependentData {
        private String dependentType;   // 依赖类型
        private String jsonpath;        // JSONPath 表达式
        private String setCache;        // 缓存键
        private String replaceKey;      // 替换键
    }
    """
    dependent_type: Text
    jsonpath: Text
    set_cache: Optional[Text]
    replace_key: Optional[Text]


class DependentCaseData(BaseModel):
    """
    依赖用例数据模型 —— 定义当前用例依赖的另一个用例

    字段说明：
    - case_id: 被依赖用例的唯一标识
    - dependent_data: 需要从被依赖用例中提取的数据列表

    YAML 示例：
    dependence_case_data:
      - case_id: "login_001"
        dependent_data:
          - dependent_type: "response"
            jsonpath: "$.data.token"
            set_cache: "token"

    Java 类比：
    public class DependentCaseData {
        private String caseId;
        private List<DependentData> dependentData;
    }
    """
    case_id: Text
    dependent_data: Union[None, List[DependentData]] = None


class ParamPrepare(BaseModel):
    """
    参数准备模型 —— 定义在调用后置接口前需要准备的参数

    字段说明：
    - dependent_type: 数据来源类型
    - jsonpath: JSONPath 提取路径
    - set_cache: 设置到缓存中的键名

    Java 类比：
    public class ParamPrepare {
        private String dependentType;
        private String jsonpath;
        private String setCache;
    }
    """
    dependent_type: Text
    jsonpath: Text
    set_cache: Text


class SendRequest(BaseModel):
    """
    发送请求模型 —— 定义在后置操作（teardown）中如何发起一个新的请求

    字段说明：
    - dependent_type: 依赖类型
    - jsonpath: JSONPath 提取路径（可选）
    - cache_data: 从缓存中读取的数据键（可选）
    - set_cache: 设置到缓存中的键（可选）
    - replace_key: 替换键（可选）

    Java 类比：
    public class SendRequest {
        private String dependentType;
        private String jsonpath;
        private String cacheData;
        private String setCache;
        private String replaceKey;
    }
    """
    dependent_type: Text
    jsonpath: Optional[Text]
    cache_data: Optional[Text]
    set_cache: Optional[Text]
    replace_key: Optional[Text]


class TearDown(BaseModel):
    """
    后置处理模型 —— 定义测试用例执行完毕后需要进行的操作

    典型场景：
    - 测试完添加接口后，自动调用删除接口清理数据
    - 测试完后执行数据库清理 SQL

    字段说明：
    - case_id: 需要执行的后置用例 ID
    - param_prepare: 执行后置用例前需要准备的参数列表
    - send_request: 后置操作中需要发起的请求列表

    Java 类比：
    public class TearDown {
        private String caseId;
        private List<ParamPrepare> paramPrepare;
        private List<SendRequest> sendRequest;
    }
    """
    case_id: Text
    param_prepare: Optional[List["ParamPrepare"]]
    send_request: Optional[List["SendRequest"]]


class CurrentRequestSetCache(BaseModel):
    """
    当前请求缓存设置模型 —— 定义如何从当前请求的响应中提取数据并缓存

    字段说明：
    - type: 缓存数据类型
    - jsonpath: JSONPath 提取路径
    - name: 缓存名称/键

    Java 类比：
    public class CurrentRequestSetCache {
        private String type;
        private String jsonpath;
        private String name;
    }
    """
    type: Text
    jsonpath: Text
    name: Text


class TestCase(BaseModel):
    """
    测试用例核心数据模型 —— 对应 YAML 中定义的单个测试用例

    这是整个框架中最重要的数据模型，YAML 用例中的所有字段都会映射到这个类

    字段说明：
    - url: 接口路径（如 "/api/v1/user/login"）
    - method: HTTP 方法（GET/POST/PUT/DELETE）
    - detail: 用例描述（如 "用户登录接口测试"）
    - assert_data: 断言数据（字典或字符串格式）
    - headers: 请求头（可选，默认为空字典）
    - requestType: 请求数据类型（JSON/PARAMS/DATA/FILE）
    - is_run: 是否执行该用例（True/False/表达式）
    - data: 请求体数据（可选）
    - dependence_case: 是否存在接口依赖（True/False）
    - dependence_case_data: 接口依赖数据列表（可选）
    - sql: 前置 SQL 查询列表（用例执行前的数据库查询）
    - setup_sql: 前置 SQL 列表（同 sql）
    - status_code: 预期 HTTP 状态码（可选）
    - teardown_sql: 后置 SQL 列表（用例执行后的数据库操作）
    - teardown: 后置处理列表（用例执行后的清理操作）
    - current_request_set_cache: 当前请求的缓存设置列表
    - sleep: 请求前的等待时间（秒）

    YAML 示例：
    - name: 登录接口测试
      url: "/api/v1/user/login"
      method: "POST"
      requestType: "JSON"
      data:
        username: "admin"
        password: "123456"
      assert:
        - jsonpath: "$.code"
          type: "=="
          value: 200

    Java 类比：
    public class TestCase {
        private String url;
        private String method;
        private String detail;
        private Object assertData;
        private Map<String, String> headers;
        private String requestType;
        private Object isRun;
        private Object data;
        private Boolean dependenceCase;
        private List<DependentCaseData> dependenceCaseData;
        private List<String> sql;
        private Integer statusCode;
        private List<TearDown> teardown;
        // ...
    }
    """
    url: Text
    method: Text
    detail: Text
    assert_data: Union[Dict, Text]
    headers: Union[None, Dict, Text] = {}
    requestType: Text
    is_run: Union[None, bool, Text] = None
    data: Any = None
    dependence_case: Union[None, bool] = False
    dependence_case_data: Optional[Union[None, List["DependentCaseData"], Text]] = None
    sql: List = None
    setup_sql: List = None
    status_code: Optional[int] = None
    teardown_sql: Optional[List] = None
    teardown: Union[List["TearDown"], None] = None
    current_request_set_cache: Optional[List["CurrentRequestSetCache"]]
    sleep: Optional[Union[int, float]]


class ResponseData(BaseModel):
    """
    响应数据模型 —— 封装接口调用后的完整响应信息

    这个模型在请求执行后创建，包含请求和响应的所有信息，
    用于断言、日志记录和报告生成。

    字段说明：
    - url: 请求的 URL
    - is_run: 是否执行
    - detail: 用例描述
    - response_data: 响应体（JSON 字符串）
    - request_body: 请求体
    - method: 请求方法
    - sql_data: 数据库查询结果
    - yaml_data: 原始 YAML 用例数据（TestCase 对象）
    - headers: 请求头
    - cookie: Cookie 数据
    - assert_data: 断言数据
    - res_time: 响应时间（毫秒或秒）
    - status_code: HTTP 状态码
    - teardown: 后置处理列表
    - teardown_sql: 后置 SQL 列表
    - body: 响应体（解析后的对象）

    Java 类比：
    public class ResponseData {
        private String url;
        private Object isRun;
        private String detail;
        private String responseData;
        private Object requestBody;
        private String method;
        private Map<String, Object> sqlData;
        private TestCase yamlData;
        private Map<String, String> headers;
        private Map<String, String> cookie;
        private Object assertData;
        private double resTime;
        private int statusCode;
        private List<TearDown> teardown;
        private List<Object> teardownSql;
        private Object body;
    }
    """
    url: Text
    is_run: Union[None, bool, Text]
    detail: Text
    response_data: Text
    request_body: Any
    method: Text
    sql_data: Dict
    yaml_data: "TestCase"
    headers: Dict
    cookie: Dict
    assert_data: Dict
    res_time: Union[int, float]
    status_code: int
    teardown: List["TearDown"] = None
    teardown_sql: Union[None, List]
    body: Any


# ==================== 配置相关数据模型 ====================

class DingTalk(BaseModel):
    """
    钉钉通知配置模型

    字段说明：
    - webhook: 钉钉机器人 Webhook 地址
    - secret: 钉钉机器人加签密钥（用于签名验证）

    Java 类比：
    public class DingTalk {
        private String webhook;
        private String secret;
    }
    """
    webhook: Union[Text, None]
    secret: Union[Text, None]


class MySqlDB(BaseModel):
    """
    MySQL 数据库配置模型

    字段说明：
    - switch: 数据库功能开关（True=启用，False=关闭）
    - host: 数据库主机地址
    - user: 数据库用户名
    - password: 数据库密码
    - port: 数据库端口（默认 3306）

    Java 类比：
    public class MySqlDB {
        private boolean switch = false;
        private String host;
        private String user;
        private String password;
        private int port = 3306;
    }
    """
    switch: bool = False
    host: Union[Text, None] = None
    user: Union[Text, None] = None
    password: Union[Text, None] = None
    port: Union[int, None] = 3306


class Webhook(BaseModel):
    """
    Webhook 通用配置模型（企业微信、飞书共用）

    字段说明：
    - webhook: Webhook 地址 URL

    Java 类比：
    public class Webhook {
        private String webhook;
    }
    """
    webhook: Union[Text, None]


class Email(BaseModel):
    """
    邮件通知配置模型

    字段说明：
    - send_user: 发件人邮箱地址
    - email_host: SMTP 服务器地址（如 smtp.qq.com）
    - stamp_key: SMTP 授权码/密钥
    - send_list: 收件人列表（逗号分隔的邮箱地址）

    Java 类比：
    public class Email {
        private String sendUser;
        private String emailHost;
        private String stampKey;
        private String sendList;
    }
    """
    send_user: Union[Text, None]
    email_host: Union[Text, None]
    stamp_key: Union[Text, None]
    # 收件人
    send_list: Union[Text, None]


class Config(BaseModel):
    """
    全局配置模型 —— 对应 config.yaml 的完整结构

    这是 config.yaml 文件的 Python 对象表示，
    所有配置项都可以在 YAML 中直接设置。

    字段说明：
    - project_name: 项目名称
    - env: 运行环境（如 dev、test、prod）
    - tester_name: 测试人员姓名
    - notification_type: 通知类型（0=不发送，1=钉钉，2=企业微信，3=邮件，4=飞书）
    - excel_report: 是否生成失败用例 Excel 报告
    - ding_talk: 钉钉配置（DingTalk 对象）
    - mysql_db: 数据库配置（MySqlDB 对象）
    - mirror_source: 镜像源地址
    - wechat: 企业微信配置（Webhook 对象）
    - email: 邮件配置（Email 对象）
    - lark: 飞书配置（Webhook 对象）
    - real_time_update_test_cases: 是否实时更新测试用例
    - host: 主服务地址
    - app_host: 应用服务地址（可选）

    Java 类比：
    @ConfigurationProperties(prefix = "config")
    public class Config {
        private String projectName;
        private String env;
        private String testerName;
        private int notificationType = 0;
        private boolean excelReport;
        private DingTalk dingTalk;
        private MySqlDB mysqlDb;
        private String mirrorSource;
        private Webhook wechat;
        private Email email;
        private Webhook lark;
        private boolean realTimeUpdateTestCases = false;
        private String host;
        private String appHost;
    }
    """
    project_name: Text
    env: Text
    tester_name: Text
    notification_type: int = 0
    excel_report: bool
    ding_talk: "DingTalk"
    mysql_db: "MySqlDB"
    mirror_source: Text
    wechat: "Webhook"
    email: "Email"
    lark: "Webhook"
    real_time_update_test_cases: bool = False
    host: Text
    app_host: Union[Text, None]


# ==================== Allure 报告相关枚举 ====================

@unique
class AllureAttachmentType(Enum):
    """
    Allure 报告附件类型枚举

    定义 Allure 报告支持的文件格式类型，
    用于在报告中正确设置附件的 MIME 类型。

    分类：
    - 文本类：TEXT, CSV, TSV, URI_LIST
    - 标记类：HTML, XML, JSON, YAML, PCAP
    - 图片类：PNG, JPG, SVG, GIF, BMP, TIFF
    - 视频类：MP4, OGG, WEBM
    - 文档类：PDF

    Java 类比：
    public enum AllureAttachmentType {
        TEXT("txt"), CSV("csv"), ..., PDF("pdf");
        private final String extension;
    }
    """
    TEXT = "txt"
    CSV = "csv"
    TSV = "tsv"
    URI_LIST = "uri"

    HTML = "html"
    XML = "xml"
    JSON = "json"
    YAML = "yaml"
    PCAP = "pcap"

    PNG = "png"
    JPG = "jpg"
    SVG = "svg"
    GIF = "gif"
    BMP = "bmp"
    TIFF = "tiff"

    MP4 = "mp4"
    OGG = "ogg"
    WEBM = "webm"

    PDF = "pdf"


@unique
class AssertMethod(Enum):
    """
    断言方法枚举 —— 定义所有支持的断言比较方式

    这些断言方法用于比较接口响应值与预期值的关系。

    比较类：
    - equals (==): 等于
    - not_equals (not_eq): 不等于
    - string_equals (str_eq): 字符串等于
    - less_than (lt): 小于
    - less_than_or_equals (le): 小于等于
    - greater_than (gt): 大于
    - greater_than_or_equals (ge): 大于等于

    长度类：
    - length_equals (len_eq): 长度等于
    - length_greater_than (len_gt): 长度大于
    - length_greater_than_or_equals (len_ge): 长度大于等于
    - length_less_than (len_lt): 长度小于
    - length_less_than_or_equals (len_le): 长度小于等于

    包含类：
    - contains: 包含（A 包含 B）
    - contained_by (contained_by): 被包含（A 被 B 包含）
    - startswith: 以...开头
    - endswith: 以...结尾

    Java 类比：
    assertThat(actual).isEqualTo(expected)         -> equals
    assertThat(actual).isLessThan(expected)        -> less_than
    assertThat(actual).contains(expected)           -> contains
    assertThat(actual).startsWith(expected)         -> startswith
    """
    equals = "=="
    less_than = "lt"
    less_than_or_equals = "le"
    greater_than = "gt"
    greater_than_or_equals = "ge"
    not_equals = "not_eq"
    string_equals = "str_eq"
    length_equals = "len_eq"
    length_greater_than = "len_gt"
    length_greater_than_or_equals = 'len_ge'
    length_less_than = "len_lt"
    length_less_than_or_equals = 'len_le'
    contains = "contains"
    contained_by = 'contained_by'
    startswith = 'startswith'
    endswith = 'endswith'
