#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/3/29 14:57
# @Author : 余少琪
# @Description: 邮件通知发送
#
# 【文件作用】
# 封装 SMTP 邮件发送功能，支持：
# 1. 测试执行完毕后的常规通知邮件
# 2. 程序异常时的错误通知邮件
#
# 【Java 对比说明】
# 类似于 Java 中使用 JavaMailSender 发送邮件：
# MimeMessage message = mailSender.createMimeMessage();
# MimeMessageHelper helper = new MimeMessageHelper(message);
# helper.setFrom("test@example.com");
# helper.setTo(recipients);
# helper.setSubject(subject);
# helper.setText(content, true);
# mailSender.send(message);
import smtplib
from email.mime.text import MIMEText
from utils.other_tools.allure_data.allure_report_data import TestMetrics, AllureFileClean
from utils import config


class SendEmail:
    """
    邮件发送器

    核心职责：
    - 发送测试执行报告邮件
    - 发送程序异常通知邮件

    Java 类比：
    public class SendEmail {
        private TestMetrics metrics;
        private String caseDetail;

        public SendEmail(TestMetrics metrics) { ... }
        public static void sendMail(List<String> users, String subject, String content) { ... }
        public void errorMail(String errorMessage) { ... }
        public void sendMain() { ... }
    }
    """
    def __init__(self, metrics: TestMetrics):
        """
        初始化邮件发送器

        Args:
            metrics: 测试执行统计数据
        """
        self.metrics = metrics
        self.allure_data = AllureFileClean()
        # 获取失败用例详情（用于邮件内容）
        self.CaseDetail = self.allure_data.get_failed_cases_detail()

    @classmethod
    def send_mail(cls, user_list: list, sub, content: str) -> None:
        """
        发送邮件

        【发送流程】
        1. 创建 MIMEText 消息
        2. 设置主题、发件人、收件人
        3. 连接 SMTP 服务器
        4. 登录并发送邮件
        5. 关闭连接

        Args:
            user_list: 收件人邮箱列表
            sub: 邮件主题
            content: 邮件内容（纯文本）

        Java 类比：
        public static void sendMail(List<String> userList, String subject, String content) {
            MimeMessage message = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(message);
            helper.setFrom(sender);
            helper.setTo(userList.toArray(new String[0]));
            helper.setSubject(subject);
            helper.setText(content);
            mailSender.send(message);
        }
        """
        user = "余少琪" + "<" + config.email.send_user + ">"
        message = MIMEText(content, _subtype='plain', _charset='utf-8')
        message['Subject'] = sub
        message['From'] = user
        message['To'] = ";".join(user_list)
        server = smtplib.SMTP()
        server.connect(config.email.email_host)
        server.login(config.email.send_user, config.email.stamp_key)
        server.sendmail(user, user_list, message.as_string())
        server.close()

    def error_mail(self, error_message: str) -> None:
        """
        发送程序异常通知邮件

        当 run.py 中发生未捕获异常时调用，包含完整的错误堆栈信息。

        Args:
            error_message: 异常堆栈信息（traceback.format_exc() 的返回值）
        """
        email = config.email.send_list
        user_list = email.split(',')  # 多个邮箱用逗号分隔

        sub = config.project_name + "接口自动化执行异常通知"
        content = f"自动化测试的执行完毕，程序中发现异常，请悉知。报错信息如下：\n{error_message}"
        self.send_mail(user_list, sub, content)

    def send_main(self) -> None:
        """
        发送测试执行报告邮件

        邮件内容包含：
        - 用例总数、通过/失败/异常/跳过数量
        - 通过率
        - 失败用例详情
        - Jenkins 报告链接
        """
        email = config.email.send_list
        user_list = email.split(',')

        sub = config.project_name + "接口自动化报告"
        content = f"""
        各位同事, 大家好:
            自动化用例执行完成，执行结果如下:
            用例运行总数: {self.metrics.total} 个
            通过用例个数: {self.metrics.passed} 个
            失败用例个数: {self.metrics.failed} 个
            异常用例个数: {self.metrics.broken} 个
            跳过用例个数: {self.metrics.skipped} 个
            成  功   率: {self.metrics.pass_rate} %

        {self.allure_data.get_failed_cases_detail()}

        **********************************
        jenkins地址：https://121.xx.xx.47:8989/login
        详细情况可登录jenkins平台查看，非相关负责人员可忽略此消息。谢谢。
        """
        self.send_mail(user_list, sub, content)


if __name__ == '__main__':
    SendEmail(AllureFileClean().get_case_count()).send_main()
