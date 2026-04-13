#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# @Time   : 2022/3/28 10:52
# @Author : 余少琪
# @Description: 定时器工具类
#
# 【文件作用】
# 提供一个定时器类 PyTimer，支持：
# 1. 一次性定时任务
# 2. 循环定时任务
# 3. 高精度定时（最小精度 10 毫秒）
#
# 【Java 对比说明】
# 类似于 Java 的 ScheduledExecutorService：
# ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(1);
# scheduler.schedule(task, delay, TimeUnit.MILLISECONDS);        // 一次性
# scheduler.scheduleAtFixedRate(task, delay, interval, MILLISECONDS); // 循环
import time
import threading


class PyTimer:
    """
    定时器类

    核心功能：
    - 在指定时间间隔后执行某个函数
    - 支持一次性执行或连续循环执行
    - 最小精度 10 毫秒

    Java 类比：
    public class PyTimer {
        private Runnable func;
        private boolean running;

        public PyTimer(Runnable func) { ... }
        public void start(double interval, boolean once) { ... }
        public void stop() { ... }
    }
    """

    def __init__(self, func, *args, **kwargs):
        """
        初始化定时器

        Args:
            func: 要定时执行的函数
            *args: 函数的位置参数
            **kwargs: 函数的关键字参数
        """
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.running = False

    def _run_func(self):
        """
        在新线程中运行定时事件函数

        使用子线程执行目标函数，避免阻塞定时器主循环。
        """
        _thread = threading.Thread(target=self.func, args=self.args, kwargs=self.kwargs)
        _thread.setDaemon(True)  # 设置为守护线程，主线程退出时自动终止
        _thread.start()

    def _start(self, interval, once):
        """
        定时器主循环线程

        【执行逻辑】
        1. 计算轮询间隔（最高精度 10ms）
        2. 循环等待直到定时时间到达
        3. 执行目标函数
        4. 如果是循环模式，更新下一次定时时间继续循环

        Args:
            interval: 定时间隔（秒）
            once: 是否只执行一次
        """
        interval = max(interval, 0.01)  # 最小间隔 10ms

        # 根据间隔大小调整轮询精度
        if interval < 0.050:
            _dt = interval / 10  # 小间隔使用更高精度轮询
        else:
            _dt = 0.005  # 默认 5ms 轮询精度

        if once:
            # 一次性定时任务
            deadline = time.time() + interval
            while time.time() < deadline:
                time.sleep(_dt)
            # 定时时间到，调用目标函数
            self._run_func()
        else:
            # 循环定时任务
            self.running = True
            deadline = time.time() + interval
            while self.running:
                while time.time() < deadline:
                    time.sleep(_dt)

                # 更新下一次定时时间
                deadline += interval

                # 定时时间到，调用目标函数
                if self.running:
                    self._run_func()

    def start(self, interval, once=False):
        """
        启动定时器

        Args:
            interval: 定时间隔（秒，浮点数），最高精度 10 毫秒
            once: 是否仅执行一次（默认 False，连续循环执行）

        示例：
        # 每 5 秒执行一次
        timer.start(5.0)

        # 3 秒后执行一次
        timer.start(3.0, once=True)
        """
        thread_ = threading.Thread(target=self._start, args=(interval, once))
        thread_.setDaemon(True)
        thread_.start()

    def stop(self):
        """
        停止定时器

        将 running 标记设为 False，终止循环定时任务。
        """
        self.running = False


def do_something(name, gender='male'):
    """示例函数：定时执行的任务"""
    print(time.time(), '定时时间到，执行特定任务')
    print('name:%s, gender:%s', name, gender)
    time.sleep(5)
    print(time.time(), '完成特定任务')


# 示例用法
timer = PyTimer(do_something, 'Alice', gender='female')
timer.start(0.5, once=False)

input('按回车键结束\n')  # 此处阻塞住进程
timer.stop()
