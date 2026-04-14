#!/usr/bin/env python
# -*- coding: utf-8 -*-


import allure
import pytest
from utils.read_files_tools.get_yaml_data_analysis import GetTestCase
from utils.assertion.assert_control import Assert
from utils.requests_tool.request_control import RequestControl
from utils.read_files_tools.regular_control import regular
from utils.requests_tool.teardown_control import TearDownHandler


# 按业务流程顺序执行：人设列表 -> 评估包列表 -> 章节预览 -> 选择/绑定 -> 验证
case_id = [
    'persona_lib_01_person_page',
    'persona_lib_02_evaluate_page',
    'persona_lib_03_chapter_list',
    'persona_lib_04_select_default',
    'persona_lib_05_bind_persona',
    'persona_lib_06_verify_refresh',
    'persona_lib_07_filter_type',
]
TestData = GetTestCase.case_data(case_id)
re_data = regular(str(TestData))


@allure.epic("培训对练系统")
@allure.feature("人设库管理")
class TestPersonaLibrary:

    @allure.story("人设库管理全流程")
    @pytest.mark.parametrize('in_data', eval(re_data), ids=[i['detail'] for i in TestData])
    def test_persona_library_flow(self, in_data, case_skip):
        """
        人设库管理模块接口测试全流程
        执行顺序：
        1. 查询人设分页列表（缓存人设ID）
        2. 获取可选评估包列表（缓存评估包ID）
        3. 预览评估包章节详情
        4. 设置默认评估包
        5. 给指定人设绑定评估包
        6. 验证绑定后列表刷新
        7. 按类型筛选人设
        """
        res = RequestControl(in_data).http_request()
        TearDownHandler(res).teardown_handle()
        Assert(in_data['assert_data']).assert_equality(
            response_data=res.response_data,
            sql_data=res.sql_data,
            status_code=res.status_code
        )


if __name__ == '__main__':
    pytest.main(['test_persona_library.py', '-s', '-W', 'ignore:Module already imported:pytest.PytestWarning'])
