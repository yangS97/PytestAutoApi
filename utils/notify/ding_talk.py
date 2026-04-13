#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/3/28 15:30
# @Author : 余少琪
# @Description: 钉钉通知封装
#
# 【文件作用】
# 封装钉钉机器人 Webhook 消息发送功能，支持：
# - 文本消息
# - Markdown 消息
# - Link 消息
# - FeedLink 消息（卡片消息）
#
# 【钉钉签名验证】
# 钉钉 Webhook 支持签名验证机制，防止消息被篡改。
# 签名算法：HmacSHA256(timestamp + "\n" + secret) -> base64 -> urlEncode
#
# 【Java 对比说明】
# 类似于 Java 中使用 HttpClient 调用钉钉 Webhook API
import base64
import hashlib
import hmac
import time
import urllib.parse
from typing import Any, Text
from dingtalkchatbot.chatbot import DingtalkChatbot, FeedLink
from utils.other_tools.get_local_ip import get_host_ip
from utils.other_tools.allure_data.allure_report_data import AllureFileClean, TestMetrics
from utils import config


class DingTalkSendMsg:
    """
    钉钉消息发送器

    核心职责：
    - 生成钉钉 Webhook 签名
    - 发送文本/Markdown/Link/FeedLink 消息
    - 发送测试报告通知

    Java 类比：
    public class DingTalkSendMsg {
        private TestMetrics metrics;
        private String timeStamp;

        public DingTalkSendMsg(TestMetrics metrics) { ... }
        public void sendDingNotification() { ... }
    }
    """
    def __init__(self, metrics: TestMetrics):
        """
        初始化钉钉消息发送器

        Args:
            metrics: 测试执行统计数据
        """
        self.metrics = metrics
        # 当前时间戳（毫秒级），用于钉钉签名
        self.timeStamp = str(round(time.time() * 1000))

    def xiao_ding(self):
        """
        创建钉钉聊天机器人实例

        拼接完整的 Webhook URL（包含时间戳和签名）。

        Returns:
            DingtalkChatbot: 钉钉机器人客户端实例
        """
        sign = self.get_sign()
        # 从配置文件中获取钉钉 Webhook 地址，拼接时间戳和签名
        webhook = config.ding_talk.webhook + "&timestamp=" + self.timeStamp + "&sign=" + sign
        return DingtalkChatbot(webhook)

    def get_sign(self) -> Text:
        """
        根据时间戳和密钥生成钉钉签名

        签名算法（HmacSHA256）：
        1. 拼接字符串：timestamp + "\n" + secret
        2. 使用 HmacSHA256 计算 HMAC 值
        3. Base64 编码
        4. URL 编码

        Returns:
            str: URL 编码后的签名值

        Java 类比：
        String stringToSign = timestamp + "\n" + secret;
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(secret.getBytes("UTF-8"), "HmacSHA256"));
        byte[] signData = mac.doFinal(stringToSign.getBytes("UTF-8"));
        String sign = URLEncoder.encode(Base64.encodeBase64String(signData));
        """
        string_to_sign = f'{self.timeStamp}\n{config.ding_talk.secret}'.encode('utf-8')
        hmac_code = hmac.new(
            config.ding_talk.secret.encode('utf-8'),
            string_to_sign,
            digestmod=hashlib.sha256).digest()

        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return sign

    def send_text(self, msg: Text, mobiles=None) -> None:
        """
        发送文本消息

        Args:
            msg: 文本内容
            mobiles: 艾特用户电话列表（可选）
        """
        if not mobiles:
            self.xiao_ding().send_text(msg=msg, is_at_all=True)
        else:
            if isinstance(mobiles, list):
                self.xiao_ding().send_text(msg=msg, at_mobiles=mobiles)
            else:
                raise TypeError("mobiles类型错误 不是list类型.")

    def send_link(self, title: Text, text: Text, message_url: Text, pic_url: Text) -> None:
        """
        发送 Link 类型消息（带标题、内容、图片和跳转链接）

        Args:
            title: 消息标题
            text: 消息内容
            message_url: 点击消息跳转的 URL
            pic_url: 图片 URL
        """
        self.xiao_ding().send_link(
            title=title, text=text, message_url=message_url, pic_url=pic_url)

    def send_markdown(self, title: Text, msg: Text, mobiles=None, is_at_all=False) -> None:
        """
        发送 Markdown 格式消息

        Args:
            title: 消息标题
            msg: Markdown 格式的内容
            mobiles: 艾特用户电话列表
            is_at_all: 是否 @所有人
        """
        if mobiles is None:
            self.xiao_ding().send_markdown(title=title, text=msg, is_at_all=is_at_all)
        else:
            if isinstance(mobiles, list):
                self.xiao_ding().send_markdown(title=title, text=msg, at_mobiles=mobiles)
            else:
                raise TypeError("mobiles类型错误 不是list类型.")

    @staticmethod
    def feed_link(title: Text, message_url: Text, pic_url: Text) -> Any:
        """
        创建 FeedLink 对象（卡片链接）

        Args:
            title: 卡片标题
            message_url: 点击跳转的 URL
            pic_url: 图片 URL

        Returns:
            FeedLink: 卡片链接对象
        """
        return FeedLink(title=title, message_url=message_url, pic_url=pic_url)

    def send_feed_link(self, *arg) -> None:
        """
        发送 FeedLink 卡片消息

        Args:
            *arg: 多个 FeedLink 对象
        """
        self.xiao_ding().send_feed_card(list(arg))

    def send_ding_notification(self):
        """
        发送钉钉测试报告通知

        【通知内容】
        - 项目名称
        - 测试环境
        - 执行人
        - 通过率、总数、成功/失败/异常/跳过数量
        - 测试报告链接

        【@规则】
        如果有失败或异常用例，则 @所有人
        """
        # 判断如果有失败的用例，@所有人
        is_at_all = False
        if self.metrics.failed + self.metrics.broken > 0:
            is_at_all = True
        text = f"#### {config.project_name}自动化通知  " \
               f"\n\n>Python脚本任务: {config.project_name}" \
               f"\n\n>环境: TEST\n\n>" \
               f"执行人: {config.tester_name}" \
               f"\n\n>执行结果: {self.metrics.pass_rate}% " \
               f"\n\n>总用例数: {self.metrics.total} " \
               f"\n\n>成功用例数: {self.metrics.passed}" \
               f" \n\n>失败用例数: {self.metrics.failed} " \
               f" \n\n>异常用例数: {self.metrics.broken} " \
               f"\n\n>跳过用例数: {self.metrics.skipped}" \
               f" ![screenshot](" \
               f"https://img.alicdn.com/tfs/TB1NwmBEL9TBuNjy1zbXXXpepXa-2400-1218.png" \
               f")\n" \
               f" > ###### 测试报告 [详情](http://{get_host_ip()}:9999/index.html) \n"
        DingTalkSendMsg(AllureFileClean().get_case_count()).send_markdown(
            title="【接口自动化通知】",
            msg=text,
            is_at_all=is_at_all
        )


if __name__ == '__main__':
    DingTalkSendMsg(AllureFileClean().get_case_count()).send_ding_notification()
