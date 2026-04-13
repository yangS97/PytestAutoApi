#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time   : 2022/3/28 15:46
# @Author : 余少琪
# @Description: 代理录制工具 —— 基于 mitmproxy 拦截 HTTP 请求转 YAML 用例
#
# 【文件作用】
# 通过 mitmproxy 代理拦截 HTTP 请求，自动将接口请求数据转换为 YAML 测试用例。
# 这样可以直接从浏览器操作中生成测试用例，而不需要手动编写 YAML。
#
# 【工作原理】
# 1. 启动 mitmproxy 代理（默认端口 8080）
# 2. 浏览器配置代理指向 mitmproxy
# 3. Counter.response() 拦截每个 HTTP 响应
# 4. 过滤非目标请求（静态资源等）
# 5. 提取请求信息（URL、方法、参数、响应等）
# 6. 生成符合框架规范的 YAML 用例
#
# 【启动命令】
# mitmweb -s ./utils/recording/mitmproxy_control.py -p 8888
#
# 【Java 对比说明】
# 类似于 Java 中使用 BrowserMob Proxy 或 ZAP 拦截请求生成测试用例

from urllib.parse import parse_qs, urlparse
from typing import Any, Union, Text, List, Dict, Tuple
import ast
import os
import mitmproxy.http
from mitmproxy import ctx
from ruamel import yaml


class Counter:
    """
    mitmproxy 插件类 —— 拦截 HTTP 响应并生成 YAML 测试用例

    mitmproxy 会在每个 HTTP 响应返回时调用 response() 方法，
    我们在这个方法中提取请求信息并写入 YAML 文件。

    参考资料: https://blog.wolfogre.com/posts/usage-of-mitmproxy/

    Java 类比：
    类似于实现 BrowserMob Proxy 的 ResponseInterceptor：
    public class Counter implements ResponseInterceptor {
        @Override
        public void process(Response response, HttpMessageContents contents, HttpMessageInfo messageInfo) {
            // 提取请求信息并生成测试用例
        }
    }
    """

    def __init__(self, filter_url: List, filename: Text = './data/proxy_data.yaml'):
        self.num = 0
        self.file = filename
        self.counter = 1
        # 需要过滤的 url
        self.url = filter_url

    def response(self, flow: mitmproxy.http.HTTPFlow) -> None:
        """
        mitmproxy 拦截 HTTP 响应的处理方法

        这是整个录制工具的核心方法，mitmproxy 会在每个 HTTP 响应返回时调用它。

        【执行流程】
        1. 过滤掉静态资源（.css/.js/.png/.jpg 等）
        2. 判断是否是目标域名（filter_url 中配置的）
        3. 提取请求信息：URL、方法、参数、响应码等
        4. 生成符合框架规范的 YAML 用例数据
        5. 写入 YAML 文件（追加模式）

        Args:
            flow: mitmproxy 的 HTTP 流对象
                  - flow.request: 请求信息（URL、方法、参数、请求头等）
                  - flow.response: 响应信息（状态码、响应体等）
        """
        # 需要过滤的文件后缀（静态资源，不生成测试用例）
        filter_url_type = ['.css', '.js', '.map', '.ico', '.png', '.woff', '.map3', '.jpeg', '.jpg']
        url = flow.request.url

        # 记录日志到 mitmproxy 控制台
        ctx.log.info("=" * 100)

        # 判断：只处理非静态资源且是目标域名的请求
        if any(i in url for i in filter_url_type) is False:
            if self.filter_url(url):

                data = self.data_handle(flow.request.text)
                method = flow.request.method
                header = self.token_handle(flow.request.headers)
                response = flow.response.text
                case_id = self.get_case_id(url) + str(self.counter)
                cases = {
                    case_id: {
                        "host": self.host_handle(url),
                        "url": self.url_path_handle(url),
                        "method": method,
                        "detail": None,
                        "headers": header,
                        'requestType': self.request_type_handler(method),
                        "is_run": True,
                        "data": data,
                        "dependence_case": None,
                        "dependence_case_data": None,
                        "assert": self.response_code_handler(response),
                        "sql": None
                    }
                }
                # 判断如果请求参数时拼接在url中，提取url中参数，转换成字典
                if "?" in url:
                    cases[case_id]['url'] = self.get_url_handler(url)[1]
                    cases[case_id]['data'] = self.get_url_handler(url)[0]

                ctx.log.info("=" * 100)
                ctx.log.info(cases)

                # 判断文件不存在则创建文件
                try:
                    self.yaml_cases(cases)
                except FileNotFoundError:
                    os.makedirs(self.file)
                self.counter += 1

    @classmethod
    def get_case_id(cls, url: Text) -> Text:
        """
        通过url，提取对应的user_id
        :param url:
        :return:
        """
        _url_path = str(url).split('?')[0]
        # 通过url中的接口地址，最后一个参数，作为case_id的名称
        _url = _url_path.split('/')
        return _url[-1]

    def filter_url(self, url: Text) -> bool:
        """过滤url"""
        for i in self.url:
            # 判断当前拦截的url地址，是否是addons中配置的host
            if i in url:
                # 如果是，则返回True
                return True
        # 否则返回 False
        return False

    @classmethod
    def response_code_handler(cls, response) -> Union[Dict, None]:
        """
        处理接口响应，默认断言数据为code码，如果接口没有code码，则返回None
        @param response:
        @return:
        """
        try:
            data = cls.data_handle(response)
            return {"code": {"jsonpath": "$.code", "type": "==",
                             "value": data['code'], "AssertType": None}}
        except KeyError:
            return None
        except NameError:
            return None

    @classmethod
    def request_type_handler(cls, method: Text) -> Text:
        """ 处理请求类型，有params、json、file,需要根据公司的业务情况自己调整 """
        if method == 'GET':
            # 如我们公司只有get请求是prams，其他都是json的
            return 'params'
        return 'json'

    @classmethod
    def data_handle(cls, dict_str) -> Any:
        """处理接口请求、响应的数据，如null、true格式问题"""
        try:
            if dict_str != "":
                if 'null' in dict_str:
                    dict_str = dict_str.replace('null', 'None')
                if 'true' in dict_str:
                    dict_str = dict_str.replace('true', 'True')
                if 'false' in dict_str:
                    dict_str = dict_str.replace('false', 'False')
                dict_str = ast.literal_eval(dict_str)
            if dict_str == "":
                dict_str = None
            return dict_str
        except Exception as exc:
            raise exc

    @classmethod
    def token_handle(cls, header) -> Dict:
        """
        提取请求头参数
        :param header:
        :return:
        """
        # 这里是将所有请求头的数据，全部都拦截出来了
        # 如果公司只需要部分参数，可以在这里加判断过滤
        headers = {}
        for key, value in header.items():
            headers[key] = value
        return headers

    def host_handle(self, url: Text) -> Tuple:
        """
        解析 url
        :param url: https://xxxx.test.xxxx.com/#/goods/listShop
        :return: https://xxxx.test.xxxx.com/
        """
        host = None
        # 循环遍历需要过滤的hosts数据
        for i in self.url:
            # 这里主要是判断，如果我们conf.py中有配置这个域名，则用例中展示 ”${{host}}“，动态获取用例host
            # 大家可以在这里改成自己公司的host地址
            if 'https://www.wanandroid.com' in url:
                host = '${{host}}'
            elif i in url:
                host = i
        return host

    def url_path_handle(self, url: Text):
        """
        解析 url_path
        :param url: https://xxxx.test.xxxx.com/shopList/json
        :return: /shopList/json
        """
        url_path = None
        # 循环需要拦截的域名
        for path in self.url:
            if path in url:
                url_path = url.split(path)[-1]
        return url_path

    def yaml_cases(self, data: Dict) -> None:
        """
        写入 yaml 数据
        :param data: 测试用例数据
        :return:
        """
        with open(self.file, "a", encoding="utf-8") as file:
            yaml.dump(data, file, Dumper=yaml.RoundTripDumper, allow_unicode=True)
            file.write('\n')

    def get_url_handler(self, url: Text) -> Tuple:
        """
        将 url 中的参数 转换成字典
        :param url: /trade?tradeNo=&outTradeId=11
        :return: {“outTradeId”: 11}
        """
        result = None
        url_path = None
        for i in self.url:
            if i in url:
                query = urlparse(url).query
                # 将字符串转换为字典
                params = parse_qs(query)
                # 所得的字典的value都是以列表的形式存在，如请求url中的参数值为空，则字典中不会有该参数
                result = {key: params[key][0] for key in params}
                url = url[0:url.rfind('?')]
                url_path = url.split(i)[-1]
        return result, url_path


# ==================== mitmproxy 插件配置 ====================

# 启动方式：
# 1. 本机设置代理，默认端口 8080
# 2. 控制台执行命令：
#    mitmweb -s ./utils/recording/mitmproxy_control.py -p 8888
# 3. 浏览器配置代理指向 127.0.0.1:8888
# 4. 访问目标网站，拦截的请求会自动转换为 YAML 用例
#
# 注意事项：
# - 需要安装 mitmproxy：pip install mitmproxy
# - 拦截的 HTTPS 需要安装 mitmproxy 的 CA 证书
# - 录制完成后，手动检查生成的 YAML 用例，补充断言数据

addons = [
    # 配置需要拦截的域名
    Counter(["https://www.wanandroid.com"])
    ]
