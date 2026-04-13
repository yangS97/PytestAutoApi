#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Time    : 2022/5/10 18:54
# @Author  : 余少琪
# @Description: 获取本机 IP 地址工具
#
# 【文件作用】
# 通过 UDP 连接外部地址的方式获取本机的局域网 IP。
# 这种方法比直接读取网卡信息更可靠，能获取到正确的出口 IP。
#
# 【Java 对比说明】
# 类似于 Java 中通过 DatagramSocket 获取本机 IP：
# DatagramSocket socket = new DatagramSocket();
# socket.connect(new InetSocketAddress("8.8.8.8", 80));
# InetAddress localAddress = socket.getLocalAddress();
"""

import socket


def get_host_ip():
    """
    查询本机局域网 IP 地址

    原理：
    1. 创建一个 UDP 套接字（不需要真正发送数据）
    2. 连接到 Google DNS 服务器（8.8.8.8:80）
    3. 获取本地绑定的 IP 地址（就是本机 IP）

    这种方法可以获取到正确的出口 IP，
    即使本机有多个网卡（如虚拟网卡、Docker 网卡等）。

    Returns:
        str: 本机 IP 地址

    Java 类比：
    public static String getHostIp() throws IOException {
        try (DatagramSocket socket = new DatagramSocket()) {
            socket.connect(InetAddress.getByName("8.8.8.8"), 80);
            return socket.getLocalAddress().getHostAddress();
        }
    }
    """
    _s = None
    try:
        # 创建 UDP 套接字
        _s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 连接到外部地址（不需要真正发送数据）
        _s.connect(('8.8.8.8', 80))
        # 获取本地绑定的 IP 地址
        l_host = _s.getsockname()[0]
    finally:
        # 确保套接字被正确关闭
        _s.close()

    return l_host
