#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/3/28 15:26
# @Author : 余少琪
# @Description: Excel 数据读写工具（旧版，已不常用）
#
# 【文件作用】
# 这个文件是早期的 Excel 数据读取工具，主要用于读取 Excel 格式的测试用例。
# 由于现在框架主要使用 YAML 格式定义用例，这个文件已不是核心功能。
#
# 支持的操作：
# 1. get_excel_data: 从 Excel 中读取指定用例的请求体和预期响应
# 2. set_excel_data: 准备 Excel 写入操作
#
# 【Java 对比说明】
# 类似于 Java 中使用 Apache POI 读取 Excel：
# Workbook workbook = WorkbookFactory(new FileInputStream(filePath));
# Sheet sheet = workbook.getSheet(sheetName);

import json

import xlrd
from xlutils.copy import copy
from common.setting import ensure_path_sep


def get_excel_data(sheet_name: str, case_name: any) -> list:
    """
    从 Excel 文件中读取指定用例的请求体和预期响应数据

    【读取规则】
    - 第 0 列是用例名称，查找匹配的行
    - 第 9 列是请求体数据
    - 第 11 列是预期响应数据（JSON 格式）

    Args:
        sheet_name: Excel 中的 sheet 页名称
        case_name: 要查找的测试用例名称

    Returns:
        list: 包含 (请求体数据, 预期响应字典) 的列表

    Java 类比：
    public static List<Tuple> getExcelData(String sheetName, String caseName) {
        // 遍历 Excel 行，匹配 caseName，提取第 9 列和第 11 列
    }
    """
    res_list = []

    excel_dire = ensure_path_sep("\\data\\TestLogin.xls")
    work_book = xlrd.open_workbook(excel_dire, formatting_info=True)

    # 打开指定的子表
    work_sheet = work_book.sheet_by_name(sheet_name)
    # 遍历第 0 列（用例名称列），查找匹配的用例
    idx = 0
    for one in work_sheet.col_values(0):
        # 匹配到用例名称，提取第 9 列（请求体）和第 11 列（预期响应）
        if case_name in one:
            req_body_data = work_sheet.cell(idx, 9).value
            resp_data = work_sheet.cell(idx, 11).value
            res_list.append((req_body_data, json.loads(resp_data)))
        idx += 1
    return res_list


def set_excel_data(sheet_index: int) -> tuple:
    """
    准备 Excel 文件用于写入操作

    Args:
        sheet_index: 要修改的 sheet 页索引

    Returns:
        tuple: (新的 Workbook 对象, 新的 Sheet 对象)

    注意：
    - 使用 xlutils.copy 复制原文件，保留原内容
    - 返回的对象可用于后续写入操作
    """
    excel_dire = '../data/TestLogin.xls'
    work_book = xlrd.open_workbook(excel_dire, formatting_info=True)
    work_book_new = copy(work_book)

    work_sheet_new = work_book_new.get_sheet(sheet_index)
    return work_book_new, work_sheet_new


if __name__ == '__main__':
    get_excel_data("异常用例", '111')
