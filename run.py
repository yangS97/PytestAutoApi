#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/3/29 15:01
# @Author : 余少琪
# @Description: 项目主入口文件，负责测试执行、报告生成、通知发送
#
# 【运行流程】
# 1. 调用 pytest.main() 执行所有测试用例
# 2. 使用 allure generate 生成 HTML 测试报告
# 3. 根据配置发送通知（钉钉/企业微信/邮件/飞书）
# 4. 可选：将失败用例导出为 Excel
# 5. 自动启动 allure serve 在浏览器中展示报告
# 6. 如发生异常，发送错误邮件通知
#
# 【Java 对比说明】
# - pytest.main() 类似于 Java 中运行 JUnit/TestNG 的 TestRunner
# - allure 类似于 Java 中的 Allure/ExtentReports 报告工具
# - os.system() 调用命令行，类似于 Java 中的 Runtime.getRuntime().exec()
import os
import sys
import traceback
import pytest
from utils.other_tools.models import NotificationType
from utils.other_tools.allure_data.allure_report_data import AllureFileClean
from utils.logging_tool.log_control import INFO
from utils.notify.wechat_send import WeChatSend
from utils.notify.ding_talk import DingTalkSendMsg
from utils.notify.send_mail import SendEmail
from utils.notify.lark import FeiShuTalkChatBot
from utils.other_tools.allure_data.error_case_excel import ErrorCaseExcel
from utils import config


def run():
    """
    主执行函数：运行测试 -> 生成报告 -> 发送通知

    Java 类比：类似于 main() 方法中的测试执行入口
    """
    try:
        # 打印项目启动 ASCII 艺术字和项目名称
        # config.project_name 从 config.yaml 中读取
        INFO.logger.info(
            """
                             _    _         _      _____         _
              __ _ _ __ (_)  / \\  _   _| |_ __|_   _|__  ___| |_
             / _` | '_ \\| | / _ \\| | | | __/ _ \\| |/ _ \\/ __| __|
            | (_| | |_) | |/ ___ \\ |_| | || (_) | |  __/\\__ \\ |_
             \\__,_| .__/|_/_/   \\_\\__,_|\\__\\___/|_|\\___||___/\\__|
                  |_|
                  开始执行{}项目...
                """.format(config.project_name)
        )

        # 【已废弃】判断现有的测试用例，如果未生成测试代码，则自动生成
        # 现在 YAML -> Python 代码的生成在测试收集阶段自动完成
        # TestCaseAutomaticGeneration().get_case_automatic()

        # ====== 第一步：执行 pytest 测试用例 ======
        # pytest.main() 参数说明：
        #   -s: 等价于 --capture=no，允许 print() 输出到控制台（不捕获标准输出）
        #   -W 'ignore:...': 忽略 "Module already imported" 警告
        #   --alluredir ./report/tmp: 将 allure 原始数据输出到 ./report/tmp 目录
        #   --clean-alluredir: 每次运行前清空 allure 数据目录
        #
        # Java 对比：类似于 JUnit 的 @RunWith 或 TestNG 的 testng.xml 配置
        # 其他可用参数（注释状态）：
        #   --reruns: 失败重跑次数
        #   --count: 重复执行次数
        #   -v: 显示详细信息和错误位置
        #   -q: 简化输出
        #   -m: 运行指定标记的测试用例（如 -m smoke）
        #   -x: 遇到第一个失败就停止
        #   --maxfail: 设置最大失败次数
        pytest.main(['-s', '-W', 'ignore:Module already imported:pytest.PytestWarning',
                     '--alluredir', './report/tmp', "--clean-alluredir"])

        # ====== 第二步：生成 Allure HTML 报告 ======
        # allure generate 命令将 ./report/tmp 的原始 JSON 数据
        # 转换为 ./report/html 的可读 HTML 报告
        # --clean 表示每次生成报告前清空旧的 HTML 输出
        os.system(r"allure generate ./report/tmp -o ./report/html --clean")

        # ====== 第三步：获取测试结果统计数据 ======
        # AllureFileClean().get_case_count() 从 allure 原始数据中提取
        # 通过/失败/跳过等统计信息，返回 TestMetrics 对象
        allure_data = AllureFileClean().get_case_count()

        # ====== 第四步：根据配置发送通知 ======
        # 通知方式映射表：枚举值 -> 对应的发送方法
        # Java 对比：类似于 Strategy 模式，通过 Map<Class, Handler> 分发
        notification_mapping = {
            NotificationType.DING_TALK.value: DingTalkSendMsg(allure_data).send_ding_notification,
            NotificationType.WECHAT.value: WeChatSend(allure_data).send_wechat_notification,
            NotificationType.EMAIL.value: SendEmail(allure_data).send_main,
            NotificationType.FEI_SHU.value: FeiShuTalkChatBot(allure_data).post
        }

        # 如果通知类型不是 DEFAULT(0=不发送)，则调用对应的通知方法
        if config.notification_type != NotificationType.DEFAULT.value:
            notification_mapping.get(config.notification_type)()

        # ====== 第五步：导出失败用例到 Excel（可选） ======
        # 如果 config.excel_report 为 True，将失败的测试用例导出为 Excel 文件
        if config.excel_report:
            ErrorCaseExcel().write_case()

        # ====== 第六步：启动 Allure 报告 Web 服务 ======
        # allure serve 会在本地启动一个 Web 服务器（127.0.0.1:9999）
        # 自动在浏览器中打开报告页面
        # 如果不想自动打开报告，可以注释掉这行
        os.system(f"allure serve ./report/tmp -h 127.0.0.1 -p 9999")

    except Exception:
        # ====== 异常处理：发送错误邮件 ======
        # traceback.format_exc() 获取完整的异常堆栈信息（类似于 Java 的 e.printStackTrace()）
        e = traceback.format_exc()
        send_email = SendEmail(AllureFileClean.get_case_count())
        send_email.error_mail(e)
        raise


if __name__ == '__main__':
    run()
