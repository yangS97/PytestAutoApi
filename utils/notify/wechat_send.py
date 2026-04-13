#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/3/29 14:59
# @Author : 余少琪
# @Description: 企业微信通知发送
#
# 【文件作用】
# 封装企业微信群机器人 Webhook 消息发送功能，支持：
# 1. 文本消息
# 2. Markdown 消息（支持颜色、加粗、链接等格式）
# 3. 文件消息（发送 Excel 报告等文件）
#
# 【企业微信 Webhook】
# 企业微信群机器人通过 Webhook URL 发送消息，
# URL 格式：https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
#
# 【Java 对比说明】
# 类似于 Java 中使用 HttpClient 调用企业微信 Webhook API
import requests
from utils.logging_tool.log_control import ERROR
from utils.other_tools.allure_data.allure_report_data import TestMetrics, AllureFileClean
from utils.times_tool.time_control import now_time
from utils.other_tools.get_local_ip import get_host_ip
from utils.other_tools.exceptions import SendMessageError, ValueTypeError
from utils import config


class WeChatSend:
    """
    企业微信群机器人消息发送器

    核心职责：
    - 发送文本消息
    - 发送 Markdown 消息
    - 发送文件消息（如 Excel 报告）
    - 发送测试报告通知

    Java 类比：
    public class WeChatSend {
        private TestMetrics metrics;
        private HttpHeaders headers;

        public WeChatSend(TestMetrics metrics) { ... }
        public void sendText(String content, List<String> phones) { ... }
        public void sendMarkdown(String content) { ... }
        public void sendFileMsg(String filePath) { ... }
        public void sendWechatNotification() { ... }
    }
    """

    def __init__(self, metrics: TestMetrics):
        """
        初始化企业微信消息发送器

        Args:
            metrics: 测试执行统计数据
        """
        self.metrics = metrics
        self.headers = {"Content-Type": "application/json"}

    def send_text(self, content, mentioned_mobile_list=None):
        """
        发送文本类型通知

        Args:
            content: 文本内容，最长不超过 2048 个字节，必须是 UTF-8 编码
            mentioned_mobile_list: 手机号列表，提醒对应的群成员（@某个成员）
        """
        _data = {"msgtype": "text", "text": {"content": content, "mentioned_list": None,
                                             "mentioned_mobile_list": mentioned_mobile_list}}

        if mentioned_mobile_list is None or isinstance(mentioned_mobile_list, list):
            # 判断手机号码列表中的数据类型，如果为 int 类型，发送的消息会乱码
            if len(mentioned_mobile_list) >= 1:
                for i in mentioned_mobile_list:
                    if isinstance(i, str):
                        res = requests.post(url=config.wechat.webhook, json=_data, headers=self.headers)
                        if res.json()['errcode'] != 0:
                            ERROR.logger.error(res.json())
                            raise SendMessageError("企业微信「文本类型」消息发送失败")
                    else:
                        raise ValueTypeError("手机号码必须是字符串类型.")
        else:
            raise ValueTypeError("手机号码列表必须是list类型.")

    def send_markdown(self, content):
        """
        发送 Markdown 类型消息

        企业微信 Markdown 支持的格式：
        - **加粗**
        - [链接](url)
        - <font color=\"info\">绿色</font>
        - <font color=\"warning\">橙色</font>
        - <font color=\"comment\">灰色</font>

        Args:
            content: Markdown 格式的消息内容
        """
        _data = {"msgtype": "markdown", "markdown": {"content": content}}
        res = requests.post(url=config.wechat.webhook, json=_data, headers=self.headers)
        if res.json()['errcode'] != 0:
            ERROR.logger.error(res.json())
            raise SendMessageError("企业微信「MarkDown类型」消息发送失败")

    def _upload_file(self, file):
        """
        将文件上传到企业微信的临时媒体库

        企业微信发送文件消息需要先上传文件到临时媒体库，
        获取 media_id 后再发送。

        Args:
            file: 文件路径

        Returns:
            str: media_id（文件标识符）
        """
        key = config.wechat.webhook.split("key=")[1]
        url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media?key={key}&type=file"
        data = {"file": open(file, "rb")}
        res = requests.post(url, files=data).json()
        return res['media_id']

    def send_file_msg(self, file):
        """
        发送文件类型的消息

        用于发送 Excel 报告等文件到企业微信群。

        Args:
            file: 文件路径
        """
        _data = {"msgtype": "file", "file": {"media_id": self._upload_file(file)}}
        res = requests.post(url=config.wechat.webhook, json=_data, headers=self.headers)
        if res.json()['errcode'] != 0:
            ERROR.logger.error(res.json())
            raise SendMessageError("企业微信「file类型」消息发送失败")

    def send_wechat_notification(self):
        """
        发送企业微信测试报告通知

        通知内容包含：
        - 项目名称
        - 测试环境
        - 测试负责人（@）
        - 通过率、总数、成功/失败/异常/跳过数量
        - 执行时长
        - 执行时间
        - 测试报告链接
        """
        text = f"""【{config.project_name}自动化通知】
                                    >测试环境：<font color=\"info\">TEST</font>
                                    >测试负责人：@{config.tester_name}
                                    >
                                    > **执行结果**
                                    ><font color=\"info\">成  功  率  : {self.metrics.pass_rate}%</font>
                                    >用例  总数：<font color=\"info\">{self.metrics.total}</font>
                                    >成功用例数：<font color=\"info\">{self.metrics.passed}</font>
                                    >失败用例数：`{self.metrics.failed}个`
                                    >异常用例数：`{self.metrics.broken}个`
                                    >跳过用例数：<font color=\"warning\">{self.metrics.skipped}个</font>
                                    >用例执行时长：<font color=\"warning\">{self.metrics.time} s</font>
                                    >时间：<font color=\"comment\">{now_time()}</font>
                                    >
                                    >非相关负责人员可忽略此消息。
                                    >测试报告，点击查看>>[测试报告入口](http://{get_host_ip()}:9999/index.html)"""

        WeChatSend(AllureFileClean().get_case_count()).send_markdown(text)


if __name__ == '__main__':
    WeChatSend(AllureFileClean().get_case_count()).send_wechat_notification()
