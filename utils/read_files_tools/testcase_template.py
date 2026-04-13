#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/4/25 20:02
# @Author : 余少琪
# @Description: Python 测试用例模板生成器
#
# 【文件作用】
# 这个文件负责将 YAML 用例数据转换为 Python pytest 测试代码并写入文件。
# 是整个框架 "YAML 驱动" 机制的最后一环。
#
# 【生成的代码结构】
# 1. 导入必要的模块（allure, pytest, 框架核心类）
# 2. 定义用例 ID 列表
# 3. 从 YAML 读取用例数据并解析动态表达式
# 4. 定义测试类（带 Allure 装饰器）
# 5. 定义测试方法（参数化执行所有用例）
#
# 【Java 对比说明】
# 类似于 Java 中通过模板引擎（如 Velocity/FreeMarker）生成代码文件：
# Template template = velocityEngine.getTemplate("testcase.vm");
# VelocityContext context = new VelocityContext();
# context.put("className", classTitle);
# template.merge(context, new FileWriter(outputFile));
import datetime
import os
from utils.read_files_tools.yaml_control import GetYamlData
from common.setting import ensure_path_sep
from utils.other_tools.exceptions import ValueNotFoundError


def write_case(case_path, page):
    """
    将测试用例代码写入 Python 文件

    Args:
        case_path: 输出文件的绝对路径
        page: 要写入的代码内容（字符串）
    """
    with open(case_path, 'w', encoding="utf-8") as file:
        file.write(page)


def write_testcase_file(*, allure_epic, allure_feature, class_title,
                        func_title, case_path, case_ids, file_name, allure_story):
    """
    生成并写入 Python 测试用例文件

    【参数说明】
    - allure_epic: Allure 报告的 Epic 标签（项目名称）
    - allure_feature: Allure 报告的 Feature 标签（模块名称）
    - allure_story: Allure 报告的 Story 标签（功能点）
    - class_title: 测试类名称（CamelCase 格式）
    - func_title: 测试函数名称
    - case_path: 输出文件的绝对路径
    - case_ids: 用例 ID 列表
    - file_name: 文件名

    【生成的代码逻辑】
    1. GetTestCase.case_data(case_id) 从缓存中读取所有用例数据
    2. regular() 解析动态表达式（如 ${{host()}}）
    3. @pytest.mark.parametrize 参数化执行所有用例
    4. 每个用例执行流程：
       a. RequestControl(in_data).http_request() 发送请求
       b. TearDownHandler(res).teardown_handle() 执行后置清理
       c. Assert(...).assert_equality(...) 执行断言验证

    Java 类比：
    类似于生成以下 Java 测试类：
    @Epic("xxx")
    @Feature("xxx")
    public class TestLogin {
        @Story("xxx")
        @ParameterizedTest
        @MethodSource("dataProvider")
        public void testLogin(TestCaseData inData) {
            ResponseData res = new RequestControl(inData).httpRequest();
            new TearDownHandler(res).teardownHandle();
            new Assert(inData.getAssertData()).assertEquality(res);
        }
    }
    """
    # 读取全局配置
    conf_data = GetYamlData(ensure_path_sep("\\common\\config.yaml")).get_yaml_data()
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    real_time_update_test_cases = conf_data['real_time_update_test_cases']

    # 模板字符串：生成 Python 测试代码
    # 这个模板会写入到每个自动生成的测试类文件中
    page = f'''#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : {now}
#
# 【文件作用】
# 此文件由框架自动生成，请勿手动修改。
# 测试数据来源于 YAML 文件，修改对应 YAML 文件即可更新测试用例。
#
# 【执行流程】
# 1. GetTestCase.case_data() 从缓存中读取 YAML 用例数据
# 2. regular() 解析动态表达式（如 ${{{{host()}}}}、$cache{{{{xxx}}}} 等）
# 3. @pytest.mark.parametrize 参数化遍历所有用例
# 4. 每个用例执行：发送请求 -> 后置清理 -> 断言验证
#
# 【Java 对比说明】
# - @allure.epic/@feature/@story 类似于 TestNG 的 @Test(description="...")
# - @pytest.mark.parametrize 类似于 JUnit 的 @ParameterizedTest + @MethodSource
# - case_skip 是 pytest fixture，用于判断是否跳过用例


import allure
import pytest
from utils.read_files_tools.get_yaml_data_analysis import GetTestCase
from utils.assertion.assert_control import Assert
from utils.requests_tool.request_control import RequestControl
from utils.read_files_tools.regular_control import regular
from utils.requests_tool.teardown_control import TearDownHandler


# 用例 ID 列表：指定要执行哪些用例
# 这些 ID 对应 YAML 文件中的用例键名
case_id = {case_ids}

# 从缓存中读取用例数据
TestData = GetTestCase.case_data(case_id)

# 解析动态表达式（如 ${{{{host()}}}}、$cache{{{{xxx}}}} 等）
re_data = regular(str(TestData))


@allure.epic("{allure_epic}")
@allure.feature("{allure_feature}")
class Test{class_title}:
    """
    测试类 —— {allure_feature}

    Java 类比：
    @Epic("{allure_epic}")
    @Feature("{allure_feature}")
    public class Test{class_title} {{ ... }}
    """

    @allure.story("{allure_story}")
    @pytest.mark.parametrize('in_data', eval(re_data), ids=[i['detail'] for i in TestData])
    def test_{func_title}(self, in_data, case_skip):
        """
        执行接口测试

        【执行步骤】
        1. RequestControl(in_data).http_request() —— 发送 HTTP 请求
        2. TearDownHandler(res).teardown_handle() —— 后置清理
        3. Assert(...).assert_equality(...) —— 断言验证

        Args:
            in_data: 当前用例的 YAML 数据（已解析动态表达式）
            case_skip: pytest fixture，自动检查是否应该跳过该用例
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
    pytest.main(['{file_name}', '-s', '-W', 'ignore:Module already imported:pytest.PytestWarning'])
'''
    # 根据配置决定是否更新测试用例文件
    if real_time_update_test_cases:
        # True: 每次运行都覆盖更新
        write_case(case_path=case_path, page=page)
    elif real_time_update_test_cases is False:
        # False: 只在文件不存在时创建（不覆盖已有文件）
        if not os.path.exists(case_path):
            write_case(case_path=case_path, page=page)
    else:
        raise ValueNotFoundError("real_time_update_test_cases 配置不正确，只能配置 True 或者 False")
