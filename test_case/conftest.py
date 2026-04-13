#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/3/30 14:12
# @Author : 余少琪
# @Description: pytest 核心配置文件（Fixtures & Hooks）
#
# 【文件作用】
# conftest.py 是 pytest 框架的共享配置文件，定义了所有测试用例共用的
# fixtures（测试夹具）和 hooks（钩子函数）。
#
# 【核心概念说明 - Java 对比】
# 1. @pytest.fixture: 类似于 Spring 的 @Bean 或 JUnit 的 @BeforeEach
#    - 用于创建测试用例的前置条件（如登录、初始化数据）
#    - 支持作用域：session（整个会话）、function（每个函数）、class（每个类）
#    - autouse=True 表示自动使用，无需在用例中显式声明
#
# 2. pytest_collection_modifyitems: pytest 钩子函数
#    - 在测试用例收集完成后调用
#    - 用于修改用例的执行顺序、名称等
#    - 类似于 TestNG 的 IMethodInterceptor
#
# 3. pytest_configure: pytest 钩子函数
#    - 在 pytest 初始化时调用
#    - 用于注册自定义标记（markers）
#
# 4. pytest_terminal_summary: pytest 钩子函数
#    - 在测试执行完毕后调用
#    - 用于收集和展示测试统计信息

import hashlib
import pytest
import time
import allure
import requests
import ast
from common.setting import ensure_path_sep
from utils.requests_tool.request_control import cache_regular
from utils.logging_tool.log_control import INFO, ERROR, WARNING
from utils.other_tools.models import TestCase
from utils.read_files_tools.clean_files import del_file
from utils.other_tools.allure_data.allure_tools import allure_step, allure_step_no
from utils.cache_process.cache_control import CacheHandler


# ==================== Session 级别 Fixtures ====================

@pytest.fixture(scope="session", autouse=False)
def clear_report():
    """
    手动清理测试报告目录

    作用：
    如果 allure 的 --clean-alluredir 无法正确删除旧报告，
    这个 fixture 可以手动删除整个 report 目录。

    注意：
    - autouse=False 表示不会自动执行，需要在用例中显式引用
    - scope="session" 表示整个测试会话只执行一次

    Java 类比：
    @BeforeAll
    public static void clearReport() { ... }
    """
    del_file(ensure_path_sep("\\report"))


@pytest.fixture(scope="session", autouse=True)
def work_login_init():
    """
    公司鉴权登录 —— 测试会话开始前自动执行

    【执行时机】
    在整个测试会话开始之前执行一次（scope="session", autouse=True），
    所有测试用例共享这个登录 token。

    【执行流程】
    1. 调用公司的登录接口 /api/v1/user/password_login
    2. 密码使用 MD5 加密后传输
    3. 从响应中提取 JWT token
    4. 将 token 存入全局缓存（CacheHandler）
    5. 后续所有需要鉴权的接口都从缓存中读取这个 token

    【Java 对比说明】
    类似于 Spring Security 的登录过滤器：
    - 在请求处理前先获取 token
    - 将 token 存储在 ThreadLocal/Session 中供后续使用

    类似于 JUnit 的：
    @BeforeAll
    public static void login() {
        String token = loginApi("admin", "password").getToken();
        TestContext.setToken(token);
    }
    """
    # 登录接口地址
    url = "https://api-test.yanjiai.com/api/v1/user/password_login"

    # 密码使用 MD5 加密（MD5 是不可逆的哈希算法）
    # "yanji2026!".encode() 将字符串转为字节流（Python 3 中字符串是 Unicode，需要编码）
    # hashlib.md5().hexdigest() 计算 MD5 哈希值（32位十六进制字符串）
    password_md5 = hashlib.md5("yanji2026!".encode()).hexdigest()

    # 登录请求体
    data = {
        "username": "13300000009",
        "password": password_md5,
        "captchaId": "",   # 验证码 ID（空表示不需要验证码）
        "captcha": ""      # 验证码（空表示不需要验证码）
    }
    headers = {'Content-Type': 'application/json'}

    # 发起 POST 请求
    # verify=True 表示验证 SSL 证书（生产环境应该为 True，测试环境有时为 False）
    res = requests.post(url=url, json=data, verify=True, headers=headers)
    response_json = res.json()

    # 从响应中提取 token
    # .get('data', {}).get('token', '') 是安全的链式取值，不会因为 key 不存在而报错
    token = response_json.get('data', {}).get('token', '')

    if token:
        # 将 token 写入全局缓存
        # cache_name='auth_token' 是缓存的键名，后续用例通过 $cache{auth_token} 读取
        CacheHandler.update_cache(cache_name='auth_token', value=token)
        INFO.logger.info("登录成功，token 已缓存")
    else:
        # 如果登录失败，记录错误响应
        ERROR.logger.error("登录失败，响应内容: %s", response_json)


# ==================== pytest Hooks（钩子函数） ====================

def pytest_collection_modifyitems(items):
    """
    测试用例收集完成后的钩子函数

    【作用 1：中文显示】
    将用例名称中的 Unicode 编码转为中文，在控制台输出时正确显示中文。
    Python 在某些终端环境下输出中文时会出现 Unicode 编码（如 \\u6d4b\\u8bd5），
    这个转换可以解决这个问题。

    【作用 2：控制执行顺序】
    默认情况下，pytest 按照文件系统中的文件顺序执行用例。
    通过这个钩子，可以重新排列用例的执行顺序。

    【执行流程】
    1. 遍历所有收集到的测试用例（items）
    2. 将用例名称转为中文显示
    3. 按照预定义的顺序重新排列用例

    Args:
        items: pytest 收集到的所有测试用例列表

    Java 类比：
    类似于 TestNG 的 IMethodInterceptor 接口，
    可以重新排列测试方法的执行顺序。
    """
    for item in items:
        # 将 Unicode 编码转为中文（解决控制台中文显示问题）
        item.name = item.name.encode("utf-8").decode("unicode_escape")
        item._nodeid = item.nodeid.encode("utf-8").decode("unicode_escape")

    # 期望的用例执行顺序（按接口依赖关系排列）
    # 例如：先执行获取用户信息，再执行添加商品，再执行购物车列表...
    appoint_items = ["test_get_user_info", "test_collect_addtool", "test_Cart_List", "test_ADD", "test_Guest_ADD",
                     "test_Clear_Cart_Item"]

    # 按指定顺序重新排列用例
    run_items = []
    for i in appoint_items:
        for item in items:
            # 提取用例名称（去除参数化部分，如 test_login[case1] -> test_login）
            module_item = item.name.split("[")[0]
            if i == module_item:
                run_items.append(item)

    # 交换位置，实现重新排序
    for i in run_items:
        run_index = run_items.index(i)
        items_index = items.index(i)

        if run_index != items_index:
            n_data = items[run_index]
            run_index = items.index(n_data)
            items[items_index], items[run_index] = items[run_index], items[items_index]


def pytest_configure(config):
    """
    pytest 初始化配置钩子

    【作用】
    注册自定义标记（markers），用于在用例上使用 @pytest.mark.标记名 进行标注。

    【已注册的标记】
    - smoke: 冒烟测试标记
    - 回归测试: 回归测试标记

    【使用方式】
    在测试用例类或方法上添加：
    @pytest.mark.smoke
    class TestLogin:
        def test_login(self): ...

    运行命令：pytest -m smoke  （只运行冒烟测试）

    Java 类比：
    类似于 TestNG 的 @Test(groups = "smoke") 注解。
    """
    config.addinivalue_line("markers", 'smoke')
    config.addinivalue_line("markers", '回归测试')


# ==================== Function 级别 Fixtures ====================

@pytest.fixture(scope="function", autouse=True)
def case_skip(in_data):
    """
    用例跳过处理 —— 每个测试用例执行前自动检查是否应该跳过

    【作用】
    检查 YAML 用例中的 is_run 字段：
    - 如果 is_run 为 False，则跳过该用例不执行
    - 如果 is_run 为 True，则正常执行
    - is_run 也可以是一个表达式（如 "${{config.env() == 'prod'}}"），
      通过 cache_regular 函数解析后判断是否执行

    【为什么需要这个功能？】
    在 YAML 用例中，我们可能希望：
    - 某些用例只在特定环境执行
    - 某些用例临时禁用但不想删除
    - 某些用例需要前置条件满足后才执行

    【执行流程】
    1. 将传入的 in_data 字典转为 TestCase 对象
    2. 解析 is_run 字段（支持表达式解析）
    3. 如果结果为 False，则在 Allure 报告中记录跳过原因，并调用 pytest.skip()

    Args:
        in_data: 当前测试用例的 YAML 数据（字典格式）

    Java 类比：
    类似于 TestNG 的：
    @BeforeMethod
    public void checkIfRun() {
        if (!isRun) {
            throw new SkipException("Skip this test");
        }
    }
    """
    # 将字典数据转为强类型的 TestCase 对象
    in_data = TestCase(**in_data)

    # 解析 is_run 字段，判断是否应该执行该用例
    # cache_regular() 函数会处理表达式解析（如 "${{config.env() == 'prod'}}"）
    # ast.literal_eval() 将字符串转为 Python 字面值（如 "False" -> False）
    if ast.literal_eval(cache_regular(str(in_data.is_run))) is False:
        # 在 Allure 报告中记录该用例的详细信息
        allure.dynamic.title(in_data.detail)
        allure_step_no(f"请求URL: {in_data.is_run}")
        allure_step_no(f"请求方式: {in_data.method}")
        allure_step("请求头: ", in_data.headers)
        allure_step("请求数据: ", in_data.data)
        allure_step("依赖数据: ", in_data.dependence_case_data)
        allure_step("预期数据: ", in_data.assert_data)

        # 跳过该用例
        pytest.skip()


# ==================== 测试结果收集 ====================

def pytest_terminal_summary(terminalreporter):
    """
    测试执行完毕后的控制台摘要输出

    【作用】
    收集并打印测试执行的统计信息：
    - 用例总数
    - 通过/失败/异常/跳过的数量
    - 用例执行时长
    - 用例成功率

    【执行时机】
    所有测试用例执行完成后自动调用

    【Java 对比说明】
    类似于 TestNG 的 ITestListener 的 onFinish() 方法，
    或 JUnit 的 TestExecutionListener 的 testPlanExecutionFinished()

    Args:
        terminalreporter: pytest 终端报告器对象，包含所有测试结果
    """
    # 统计各类用例数量
    # terminalreporter.stats 是一个字典，key 为状态（passed/failed/error/skipped），
    # value 为对应的测试报告对象列表
    # if i.when != 'teardown' 是排除后置处理阶段的报告（只统计实际测试阶段）
    _PASSED = len([i for i in terminalreporter.stats.get('passed', []) if i.when != 'teardown'])
    _ERROR = len([i for i in terminalreporter.stats.get('error', []) if i.when != 'teardown'])
    _FAILED = len([i for i in terminalreporter.stats.get('failed', []) if i.when != 'teardown'])
    _SKIPPED = len([i for i in terminalreporter.stats.get('skipped', []) if i.when != 'teardown'])

    # 用例总数（pytest 收集的总用例数）
    _TOTAL = terminalreporter._numcollected

    # 计算执行时长
    # getattr(terminalreporter, '_sessionstarttime', time.time()) 安全地获取会话开始时间
    # 如果 _sessionstarttime 不存在，则使用当前时间（时长为 0）
    _TIMES = time.time() - getattr(terminalreporter, '_sessionstarttime', time.time())

    # 打印统计信息（使用不同级别的日志，方便区分）
    # ERROR 级别：失败用例数（重要）
    # WARNING 级别：跳过用例数（需要关注）
    # INFO 级别：总数、通过率（常规信息）
    INFO.logger.error(f"用例总数: {_TOTAL}")
    INFO.logger.error(f"异常用例数: {_ERROR}")
    ERROR.logger.error(f"失败用例数: {_FAILED}")
    WARNING.logger.warning(f"跳过用例数: {_SKIPPED}")
    INFO.logger.info("用例执行时长: %.2f" % _TIMES + " s")

    # 计算通过率
    # %.2f 表示保留两位小数
    try:
        _RATE = _PASSED / _TOTAL * 100
        INFO.logger.info("用例成功率: %.2f" % _RATE + " %")
    except ZeroDivisionError:
        # 如果没有用例（_TOTAL 为 0），则通过率为 0
        INFO.logger.info("用例成功率: 0.00 %")
