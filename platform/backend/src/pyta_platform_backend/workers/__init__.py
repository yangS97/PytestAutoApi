"""worker 相关边界定义。"""

from pyta_platform_backend.workers.dispatcher import DispatchTask, MemoryRunDispatcher

# 这里故意不在包入口直接导入 runner。
# 原因是 run_service 会依赖 dispatcher，而 runner 又会依赖 run_service。
# 如果在 __init__ 里把所有对象都一次性导入，很容易形成循环依赖。
#
# 结论：
# - 常用且底层的 dispatcher 可以在这里直接导出
# - 更上层的 runner 让调用方按需从 `workers.runner` 显式导入
__all__ = ["DispatchTask", "MemoryRunDispatcher"]
