"""worker 投递边界。"""

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class DispatchTask:
    """发给 worker 的任务载荷。"""

    run_id: str
    suite_id: str
    trigger_source: str
    requested_by: str
    payload: dict[str, object]
    dispatched_at: datetime


class MemoryRunDispatcher:
    """内存版 dispatcher。

    第一阶段不上重队列，所以这里先保留一个轻量投递器边界。
    真实接入轻量 worker、消息通道或进程池时，只需要替换这个实现。
    """

    def __init__(self, channel_name: str = "memory-worker") -> None:
        self.channel_name = channel_name
        self.dispatched_tasks: list[DispatchTask] = []

    def dispatch(self, task: DispatchTask) -> None:
        """记录一次任务投递。"""

        self.dispatched_tasks.append(
            DispatchTask(
                run_id=task.run_id,
                suite_id=task.suite_id,
                trigger_source=task.trigger_source,
                requested_by=task.requested_by,
                payload=deepcopy(task.payload),
                dispatched_at=task.dispatched_at,
            )
        )

    def pull_next(self) -> Optional[DispatchTask]:
        """按先进先出顺序取出一个待执行任务。

        第一阶段先用最简单的内存队列表达 worker 边界：
        - dispatcher 负责排队
        - worker 负责取任务并执行
        """

        if not self.dispatched_tasks:
            return None
        return self.dispatched_tasks.pop(0)
