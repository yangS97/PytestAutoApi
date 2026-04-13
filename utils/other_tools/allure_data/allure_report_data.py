#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/8/06 15:44
# @Author : 余少琪
# @Description: Allure 报告数据提取
#
# 【文件作用】
# 从 Allure 生成的 HTML 报告中提取测试执行数据，
# 包括：用例统计、失败用例详情、通过率等。
# 这些数据用于：
# 1. 通知消息（钉钉/企业微信/飞书/邮件）中的统计数据
# 2. 失败用例 Excel 导出
#
# 【Allure 报告结构】
# report/html/
# ├── data/test-cases/   # 每个用例的执行详情（JSON 格式）
# ├── widgets/summary.json  # 测试执行统计汇总
# └── index.html         # 报告主页
#
# 【Java 对比说明】
# 类似于 Java 中解析 Allure 报告获取测试统计：
# 读取 widgets/summary.json 获取通过率、失败数等
import json
from typing import List, Text
from common.setting import ensure_path_sep
from utils.read_files_tools.get_all_files_path import get_all_files
from utils.other_tools.models import TestMetrics


class AllureFileClean:
    """
    Allure 报告数据清洗器

    核心职责：
    - 从 Allure 报告中提取用例执行统计
    - 获取失败用例的详情
    - 计算通过率和执行时长

    Java 类比：
    public class AllureFileClean {
        public List<Map<String, Object>> getTestcases() { ... }
        public List<String[]> getFailedCases() { ... }
        public TestMetrics getCaseCount() { ... }
    }
    """

    @classmethod
    def get_testcases(cls) -> List:
        """
        获取 Allure 报告中所有测试用例的执行情况

        从 report/html/data/test-cases/ 目录下读取每个用例的 JSON 文件。

        Returns:
            List: 所有用例的执行数据列表

        Java 类比：
        public static List<Map<String, Object>> getTestcases() {
            List<Map<String, Object>> files = new ArrayList<>();
            for (File file : testCasesDir.listFiles()) {
                files.add(new ObjectMapper().readValue(file, Map.class));
            }
            return files;
        }
        """
        # 将所有数据都收集到 files 中
        files = []
        for i in get_all_files(ensure_path_sep("\\report\\html\\data\\test-cases")):
            with open(i, 'r', encoding='utf-8') as file:
                date = json.load(file)
                files.append(date)
        return files

    def get_failed_case(self) -> List:
        """
        获取所有失败的用例标题和代码路径

        失败包括两种状态：
        - 'failed': 断言失败
        - 'broken': 执行异常（代码错误）

        Returns:
            List: 失败用例列表，每项为 (用例名称, 完整路径)

        示例：
        [('test_login', 'test_case.Login.test_login'),
         ('test_add_tool', 'test_case.Collect.test_collect_addtool')]
        """
        error_case = []
        for i in self.get_testcases():
            if i['status'] == 'failed' or i['status'] == 'broken':
                error_case.append((i['name'], i['fullName']))
        return error_case

    def get_failed_cases_detail(self) -> Text:
        """
        获取所有失败用例的格式化文本

        Returns:
            str: 格式化的失败用例列表（用于通知消息）

        示例输出：
        失败用例:
            **********************************
            test_login: test_case.Login.test_login
            test_add_tool: test_case.Collect.test_collect_addtool
        """
        date = self.get_failed_case()
        values = ""
        # 判断有失败用例，则返回内容
        if len(date) >= 1:
            values = "失败用例:\n"
            values += "        **********************************\n"
            for i in date:
                values += "        " + i[0] + ":" + i[1] + "\n"
        return values

    @classmethod
    def get_case_count(cls) -> "TestMetrics":
        """
        统计用例数量并计算通过率

        从 Allure 报告的 summary.json 中提取统计数据。

        返回的 TestMetrics 包含：
        - passed: 通过的用例数
        - failed: 失败的用例数
        - broken: 异常的用例数
        - skipped: 跳过的用例数
        - total: 总用例数
        - pass_rate: 通过率（百分比）
        - time: 执行时长（秒）

        Returns:
            TestMetrics: 用例执行统计数据

        Raises:
            FileNotFoundError: 如果 Allure 报告未生成

        Java 类比：
        public static TestMetrics getCaseCount() {
            Map<String, Object> summary = readSummaryJson();
            Map<String, Object> statistic = summary.get("statistic");
            TestMetrics metrics = new TestMetrics();
            metrics.setPassed((int) statistic.get("passed"));
            metrics.setFailed((int) statistic.get("failed"));
            metrics.setTotal((int) statistic.get("total"));
            metrics.setPassRate(metrics.getPassed() * 100.0 / metrics.getTotal());
            return metrics;
        }
        """
        try:
            file_name = ensure_path_sep("\\report\\html\\widgets\\summary.json")
            with open(file_name, 'r', encoding='utf-8') as file:
                data = json.load(file)
            _case_count = data['statistic']
            _time = data['time']
            keep_keys = {"passed", "failed", "broken", "skipped", "total"}
            run_case_data = {k: v for k, v in data['statistic'].items() if k in keep_keys}
            # 判断运行用例总数大于 0
            if _case_count["total"] > 0:
                # 计算用例成功率（通过的 + 跳过的）/ 总数
                run_case_data["pass_rate"] = round(
                    (_case_count["passed"] + _case_count["skipped"]) / _case_count["total"] * 100, 2
                )
            else:
                # 如果未运行用例，则通过率为 0.0
                run_case_data["pass_rate"] = 0.0
            # 收集用例运行时长
            run_case_data['time'] = _time if run_case_data['total'] == 0 else round(_time['duration'] / 1000, 2)
            return TestMetrics(**run_case_data)
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                "程序中检查到您未生成allure报告，"
                "通常可能导致的原因是allure环境未配置正确，"
                "详情可查看如下博客内容："
                "https://blog.csdn.net/weixin_43865008/article/details/124332793"
            ) from exc


if __name__ == '__main__':
    AllureFileClean().get_case_count()
