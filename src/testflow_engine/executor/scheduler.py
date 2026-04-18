"""
轻量调度骨架。

这里不是完整任务系统，只是先定义最小 worker/调度落点，
让平台之后能把“待执行 run”排队，再交给独立引擎消费。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from ..models import TestRunDefinition


class ScheduledJob(BaseModel):
    """待执行任务描述。"""

    run: TestRunDefinition
    run_at: datetime
    priority: int = 0
    worker_hint: Optional[str] = None


class InMemoryScheduler:
    """
    仅用于骨架阶段和单元测试的内存调度器。

    后续换成 Redis / DB / MQ 时，可以保持提交接口不变。
    """

    def __init__(self) -> None:
        self._jobs: list[ScheduledJob] = []

    def submit(self, job: ScheduledJob) -> None:
        """提交任务，并按执行时间和优先级排序。"""

        self._jobs.append(job)
        self._jobs.sort(key=lambda item: (item.run_at, -item.priority))

    def next_job(self) -> Optional[ScheduledJob]:
        """取出下一条待执行任务。"""

        if not self._jobs:
            return None
        return self._jobs.pop(0)

    def size(self) -> int:
        """当前队列长度。"""

        return len(self._jobs)
