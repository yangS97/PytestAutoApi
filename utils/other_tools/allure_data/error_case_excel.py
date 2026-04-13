#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time    : 2022/5/8 21:37
# @Author  : 余少琪
# @Email   : 1603453211@qq.com
# @Description: 失败用例 Excel 报告生成器
#
# 【文件作用】
# 从 Allure 报告中提取所有失败的测试用例详情，
# 并将它们整理成一份格式化的 Excel 报告。
# 报告包含：用例 ID、名称、URL、请求方式、请求头、
# 请求数据、依赖数据、断言数据、SQL、响应内容、执行时长等。
#
# 【执行流程】
# 1. 从 Allure 报告中读取所有失败用例的 JSON 数据
# 2. 从每个用例中提取必要的字段
# 3. 将数据写入 Excel 模板文件
# 4. 通过企业微信发送 Excel 报告
#
# 【Java 对比说明】
# 类似于 Java 中使用 Apache POI 生成 Excel 报告：
# Workbook wb = new XSSFWorkbook(templatePath);
# Sheet sheet = wb.getSheet("异常用例");
# for (FailedCase testCase : failedCases) {
#     Row row = sheet.createRow(rowIndex++);
#     row.createCell(0).setCellValue(testCase.getUid());
#     // ...
# }
import json
import shutil
import ast
import xlwings
from common.setting import ensure_path_sep
from utils.read_files_tools.get_all_files_path import get_all_files
from utils.notify.wechat_send import WeChatSend
from utils.other_tools.allure_data.allure_report_data import AllureFileClean


# TODO 还需要处理动态值
class ErrorTestCase:
    """
    失败用例数据提取器

    从 Allure 报告的 JSON 数据中提取失败用例的所有必要字段。

    Java 类比：
    public class ErrorTestCase {
        private String testCasesPath;

        public List<Map<String, Object>> getErrorCaseData() { ... }
        public String getCaseUrl(Map<String, Object> testCase) { ... }
        public String getMethod(Map<String, Object> testCase) { ... }
    }
    """
    def __init__(self):
        # Allure 报告中测试用例数据的目录路径
        self.test_case_path = ensure_path_sep("\\report\\html\\data\\test-cases\\")

    def get_error_case_data(self):
        """
        收集所有失败用例的数据

        Returns:
            list: 所有失败用例的 JSON 数据列表
        """
        path = get_all_files(self.test_case_path)
        files = []
        for i in path:
            with open(i, 'r', encoding='utf-8') as file:
                date = json.load(file)
                # 收集执行失败的用例数据
                # status='failed' 表示断言失败
                # status='broken' 表示执行异常
                if date['status'] == 'failed' or date['status'] == 'broken':
                    files.append(date)
        print(files)
        return files

    @classmethod
    def get_case_name(cls, test_case):
        """
        提取测试用例名称

        从用例名称中去掉参数化部分（如 test_login[case1] -> case1）。

        Args:
            test_case: 用例数据字典

        Returns:
            str: 用例名称
        """
        name = test_case['name'].split('[')
        case_name = name[1][:-1]
        return case_name

    @classmethod
    def get_parameters(cls, test_case):
        """
        获取 allure 报告中的 parameters 参数内容

        这些是请求前的数据，用于兼容用例执行异常、未发送请求的情况。

        Args:
            test_case: 用例数据字典

        Returns:
            dict: 请求参数数据
        """
        parameters = test_case['parameters'][0]['value']
        return ast.literal_eval(parameters)

    @classmethod
    def get_test_stage(cls, test_case):
        """
        获取 allure 报告中的 testStage 步骤数据

        这些是请求后的数据（响应信息、断言结果等）。

        Args:
            test_case: 用例数据字典

        Returns:
            list: 测试步骤列表
        """
        test_stage = test_case['testStage']['steps']
        return test_stage

    def get_case_url(self, test_case):
        """
        获取测试用例的 URL

        根据用例状态（broken/failed）从不同位置提取 URL。

        Args:
            test_case: 用例数据字典

        Returns:
            str: 请求 URL
        """
        # 判断用例步骤中的数据是否异常
        if test_case['testStage']['status'] == 'broken':
            # 如果异常状态下，则获取请求前的数据
            _url = self.get_parameters(test_case)['url']
        else:
            # 否则从请求步骤中获取 URL
            # 如果涉及到依赖，会获取多组数据，只取最后一组
            _url = self.get_test_stage(test_case)[-7]['name'][7:]
        return _url

    def get_method(self, test_case):
        """
        获取用例中的请求方式（GET/POST/PUT/DELETE）

        Args:
            test_case: 用例数据字典

        Returns:
            str: HTTP 方法
        """
        if test_case['testStage']['status'] == 'broken':
            _method = self.get_parameters(test_case)['method']
        else:
            _method = self.get_test_stage(test_case)[-6]['name'][6:]
        return _method

    def get_headers(self, test_case):
        """
        获取用例中的请求头

        Args:
            test_case: 用例数据字典

        Returns:
            dict: 请求头字典
        """
        if test_case['testStage']['status'] == 'broken':
            _headers = self.get_parameters(test_case)['headers']
        else:
            # 如果用例请求成功，则从 allure 附件中获取请求头部信息
            _headers_attachment = self.get_test_stage(test_case)[-5]['attachments'][0]['source']
            path = ensure_path_sep("\\report\\html\\data\\attachments\\" + _headers_attachment)
            with open(path, 'r', encoding='utf-8') as file:
                _headers = json.load(file)
        return _headers

    def get_request_type(self, test_case):
        """
        获取用例的请求类型（JSON/PARAMS/DATA/FILE）

        Args:
            test_case: 用例数据字典

        Returns:
            str: 请求类型
        """
        request_type = self.get_parameters(test_case)['requestType']
        return request_type

    def get_case_data(self, test_case):
        """
        获取用例的请求体内容

        Args:
            test_case: 用例数据字典

        Returns:
            dict: 请求体数据
        """
        if test_case['testStage']['status'] == 'broken':
            _case_data = self.get_parameters(test_case)['data']
        else:
            # 从 allure 附件中获取请求数据
            _case_data_attachments = self.get_test_stage(test_case)[-4]['attachments'][0]['source']
            path = ensure_path_sep("\\report\\html\\data\\attachments\\" + _case_data_attachments)
            with open(path, 'r', encoding='utf-8') as file:
                _case_data = json.load(file)
        return _case_data

    def get_dependence_case(self, test_case):
        """
        获取用例的依赖数据

        Args:
            test_case: 用例数据字典

        Returns:
            dict: 依赖数据
        """
        _dependence_case_data = self.get_parameters(test_case)['dependence_case_data']
        return _dependence_case_data

    def get_sql(self, test_case):
        """
        获取用例的 SQL 数据

        Args:
            test_case: 用例数据字典

        Returns:
            list: SQL 数据
        """
        sql = self.get_parameters(test_case)['sql']
        return sql

    def get_assert(self, test_case):
        """
        获取用例的断言数据

        Args:
            test_case: 用例数据字典

        Returns:
            dict: 断言数据
        """
        assert_data = self.get_parameters(test_case)['assert_data']
        return assert_data

    @classmethod
    def get_response(cls, test_case):
        """
        获取用例的响应内容

        根据用例状态从不同位置提取响应数据。

        Args:
            test_case: 用例数据字典

        Returns:
            dict/str: 响应内容；如果未获取到则返回 None
        """
        if test_case['testStage']['status'] == 'broken':
            # 异常状态：从 statusMessage 中获取
            _res_date = test_case['testStage']['statusMessage']
        else:
            try:
                # 正常状态：从附件中获取响应数据
                res_data_attachments = \
                    test_case['testStage']['steps'][-1]['attachments'][0]['source']
                path = ensure_path_sep("\\report\\html\\data\\attachments\\" + res_data_attachments)
                with open(path, 'r', encoding='utf-8') as file:
                    _res_date = json.load(file)
            except FileNotFoundError:
                # 程序中没有提取到响应数据，返回 None
                _res_date = None
        return _res_date

    @classmethod
    def get_case_time(cls, test_case):
        """
        获取用例运行时长

        Args:
            test_case: 用例数据字典

        Returns:
            str: 执行时长（如 "1234ms"）
        """
        case_time = str(test_case['time']['duration']) + "ms"
        return case_time

    @classmethod
    def get_uid(cls, test_case):
        """
        获取 allure 报告中的用例唯一标识

        Args:
            test_case: 用例数据字典

        Returns:
            str: 用例 UID
        """
        uid = test_case['uid']
        return uid


class ErrorCaseExcel:
    """
    失败用例 Excel 报告生成器

    核心职责：
    - 从 Allure 报告中提取失败用例
    - 使用 xlwings 操作 Excel 写入数据
    - 通过企业微信发送 Excel 报告

    Java 类比：
    public class ErrorCaseExcel {
        private String filePath;
        private App app;
        private Workbook wBook;
        private Sheet sheet;

        public ErrorCaseExcel() {
            this.app = new xlwings.App(false, false);
            this.wBook = app.books.open(filePath);
            this.sheet = wBook.sheets["异常用例"];
        }

        public void writeCase() { ... }
    }
    """
    def __init__(self):
        # Excel 模板路径
        _excel_template = ensure_path_sep("\\utils\\other_tools\\allure_data\\自动化异常测试用例.xlsx")
        self._file_path = ensure_path_sep("\\Files\\" + "自动化异常测试用例.xlsx")

        # 复制模板文件到输出路径
        shutil.copyfile(src=_excel_template, dst=self._file_path)
        # 打开 Excel 程序（不可见模式，不创建新工作簿）
        self.app = xlwings.App(visible=False, add_book=False)
        self.w_book = self.app.books.open(self._file_path, read_only=False)

        # 选取工作表
        self.sheet = self.w_book.sheets['异常用例']
        self.case_data = ErrorTestCase()

    def background_color(self, position: str, rgb: tuple):
        """
        设置 Excel 单元格背景色

        Args:
            position: 单元格位置（如 "A1", "B2"）
            rgb: RGB 颜色元组（如 (255, 0, 0)）

        Returns:
            tuple: RGB 颜色值
        """
        rng = self.sheet.range(position)
        excel_rgb = rng.color = rgb
        return excel_rgb

    def column_width(self, position: str, width: int):
        """
        设置 Excel 列宽

        Args:
            position: 列位置（如 "A", "B"）
            width: 宽度值

        Returns:
            int: 列宽
        """
        rng = self.sheet.range(position)
        excel_column_width = rng.column_width = width
        return excel_column_width

    def row_height(self, position, height):
        """
        设置 Excel 行高

        Args:
            position: 行位置（如 "1", "2"）
            height: 高度值

        Returns:
            float: 行高
        """
        rng = self.sheet.range(position)
        excel_row_height = rng.row_height = height
        return excel_row_height

    def column_width_adaptation(self, position):
        """
        Excel 所有列宽度自适应

        Args:
            position: 单元格范围（如 "A1:L100"）

        Returns:
            自适应操作结果
        """
        rng = self.sheet.range(position)
        auto_fit = rng.columns.autofit()
        return auto_fit

    def row_width_adaptation(self, position):
        """
        Excel 设置所有行宽自适应

        Args:
            position: 单元格范围

        Returns:
            自适应操作结果
        """
        rng = self.sheet.range(position)
        row_adaptation = rng.rows.autofit()
        return row_adaptation

    def write_excel_content(self, position: str, value: str):
        """
        在 Excel 单元格中写入内容

        Args:
            position: 单元格位置（如 "A2"）
            value: 要写入的值
        """
        self.sheet.range(position).value = value

    def write_case(self):
        """
        将失败用例数据写入 Excel 报告

        【执行流程】
        1. 获取所有失败用例数据
        2. 从第 2 行开始，逐行写入数据
        3. 保存并关闭 Excel
        4. 通过企业微信发送 Excel 文件

        Excel 列对应关系：
        A: 用例 UID
        B: 用例名称
        C: 请求 URL
        D: 请求方式
        E: 请求类型
        F: 请求头
        G: 请求数据
        H: 依赖数据
        I: 断言数据
        J: SQL
        K: 执行时长
        L: 响应内容
        """
        _data = self.case_data.get_error_case_data()
        # 判断有数据才进行写入
        if len(_data) > 0:
            num = 2  # 从第 2 行开始写入（第 1 行是表头）
            for data in _data:
                self.write_excel_content(position="A" + str(num), value=str(self.case_data.get_uid(data)))
                self.write_excel_content(position='B' + str(num), value=str(self.case_data.get_case_name(data)))
                self.write_excel_content(position="C" + str(num), value=str(self.case_data.get_case_url(data)))
                self.write_excel_content(position="D" + str(num), value=str(self.case_data.get_method(data)))
                self.write_excel_content(position="E" + str(num), value=str(self.case_data.get_request_type(data)))
                self.write_excel_content(position="F" + str(num), value=str(self.case_data.get_headers(data)))
                self.write_excel_content(position="G" + str(num), value=str(self.case_data.get_case_data(data)))
                self.write_excel_content(position="H" + str(num), value=str(self.case_data.get_dependence_case(data)))
                self.write_excel_content(position="I" + str(num), value=str(self.case_data.get_assert(data)))
                self.write_excel_content(position="J" + str(num), value=str(self.case_data.get_sql(data)))
                self.write_excel_content(position="K" + str(num), value=str(self.case_data.get_case_time(data)))
                self.write_excel_content(position="L" + str(num), value=str(self.case_data.get_response(data)))
                num += 1
            # 保存并关闭 Excel
            self.w_book.save()
            self.w_book.close()
            self.app.quit()
            # 有数据才发送企业微信通知
            WeChatSend(AllureFileClean().get_case_count()).send_file_msg(self._file_path)


if __name__ == '__main__':
    ErrorCaseExcel().write_case()
