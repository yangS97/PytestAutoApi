#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022-08-17 10:12:54
# @Description: 登录模块测试类
#
# 【文件作用】
# 这是登录模块的测试类，负责执行登录相关的接口测试。
# 测试数据从 data/Login/login.yaml 文件中读取。
#
# 【执行流程】
# 1. GetTestCase.case_data() 从缓存中读取 YAML 用例数据
# 2. regular() 解析动态表达式（如 ${{host()}}）
# 3. @pytest.mark.parametrize 参数化遍历所有用例
# 4. 每个用例执行：发送请求 -> 后置清理 -> 断言验证
#
# 【Java 对比说明】
# - @allure.epic/@feature/@story 类似于 TestNG 的 @Test(description="...")
# - @pytest.mark.parametrize 类似于 JUnit 的 @ParameterizedTest + @MethodSource
# - case_skip 是 pytest fixture，用于判断是否跳过用例（类似 TestNG 的 SkipException）

import allure
import pytest
from utils.read_files_tools.get_yaml_data_analysis import GetTestCase
from utils.assertion.assert_control import Assert
from utils.requests_tool.request_control import RequestControl
from utils.read_files_tools.regular_control import regular
from utils.requests_tool.teardown_control import TearDownHandler


# 用例 ID 列表：指定要执行哪些用例
# 这些 ID 对应 data/Login/login.yaml 中的用例键名
case_id = ['login_01', 'login_02', 'login_03']

# 从缓存中读取用例数据
TestData = GetTestCase.case_data(case_id)

# 解析动态表达式（如 ${{host()}}、$cache{xxx} 等）
re_data = regular(str(TestData))


@allure.epic("开发平台接口")
@allure.feature("登录模块")
class TestLogin:
    """
    登录接口测试类

    测试场景：
    - 正常登录成功
    - 密码错误登录失败
    - 账号不存在等

    Java 类比：
    @Epic("开发平台接口")
    @Feature("登录模块")
    public class TestLogin { ... }
    """

    @allure.story("登录")
    @pytest.mark.parametrize('in_data', eval(re_data), ids=[i['detail'] for i in TestData])
    def test_login(self, in_data, case_skip):
        """
        执行登录接口测试

        【执行步骤】
        1. RequestControl(in_data).http_request() —— 发送 HTTP 请求
           - 处理接口依赖（如果有）
           - 注入鉴权 token
           - 根据 requestType 发送请求
           - 封装响应为 ResponseData 对象
           - 写入 Allure 报告
           - 缓存响应数据（如果配置了）

        2. TearDownHandler(res).teardown_handle() —— 后置清理
           - 执行 teardown 中定义的清理操作
           - 执行 teardown_sql 清理数据库数据

        3. Assert(...).assert_equality(...) —— 断言验证
           - 通过 JSONPath 从响应中提取目标值
           - 执行断言比较（支持 15+ 种断言类型）
           - 支持 SQL 数据库断言

        Args:
            in_data: 当前用例的 YAML 数据（已解析动态表达式）
            case_skip: pytest fixture，自动检查是否应该跳过该用例

        Java 类比：
        @Story("登录")
        @ParameterizedTest
        @MethodSource("dataProvider")
        public void testLogin(Map<String, Object> inData) {
            ResponseData res = new RequestControl(inData).httpRequest();
            new TearDownHandler(res).teardownHandle();
            new Assert(inData.get("assert_data")).assertEquality(res);
        }
        """
        # 第一步：发送 HTTP 请求
        res = RequestControl(in_data).http_request()

        # 第二步：执行后置清理（删除测试数据等）
        TearDownHandler(res).teardown_handle()

        # 第三步：断言验证（验证响应数据和数据库数据）
        Assert(in_data['assert_data']).assert_equality(
            response_data=res.response_data,
            sql_data=res.sql_data,
            status_code=res.status_code
        )


if __name__ == '__main__':
    pytest.main(['test_login.py', '-s', '-W', 'ignore:Module already imported:pytest.PytestWarning'])
