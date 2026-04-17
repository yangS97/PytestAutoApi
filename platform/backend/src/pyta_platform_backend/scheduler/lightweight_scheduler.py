"""轻量 scheduler 骨架。"""

from dataclasses import dataclass
from typing import Callable, Dict, List


@dataclass(frozen=True)
class ScheduledJob:
    """调度任务定义。"""

    job_id: str
    description: str
    interval_seconds: int
    handler: Callable[[], None]


class LightweightScheduler:
    """第一阶段的轻量调度器。

    它的职责是管理“哪些任务该被触发”，而不是亲自执行长时间业务。
    当某个定时任务到点时，scheduler 应该调用一个很薄的 handler，
    由 handler 去创建 run / 投递 worker，而不是在 scheduler 里塞入执行引擎逻辑。
    """

    def __init__(self, poll_interval_seconds: int = 30) -> None:
        self.poll_interval_seconds = poll_interval_seconds
        self._jobs: Dict[str, ScheduledJob] = {}

    def register_job(self, job: ScheduledJob) -> None:
        """注册或覆盖一个调度任务。"""

        self._jobs[job.job_id] = job

    def list_jobs(self) -> List[ScheduledJob]:
        """返回当前已注册的任务。"""

        return list(self._jobs.values())

    def run_once(self) -> List[str]:
        """执行一次调度扫描。

        骨架阶段不实现复杂的时间轮或持久化状态，只用来表达调度边界。
        返回值保留为已执行 job_id 列表，方便未来做监控或测试。
        """

        executed_job_ids: List[str] = []
        for job in self._jobs.values():
            job.handler()
            executed_job_ids.append(job.job_id)
        return executed_job_ids
