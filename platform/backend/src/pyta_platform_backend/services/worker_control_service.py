"""worker 本地控制服务。"""

from pyta_platform_backend.schemas.worker import RunNextResponse


class WorkerControlService:
    """给本地开发提供一个最小的 worker 控制入口。"""

    def __init__(self, worker_runner) -> None:
        self._worker_runner = worker_runner

    def run_next(self) -> RunNextResponse:
        """消费一条排队中的任务。"""

        detail = self._worker_runner.run_next()
        return RunNextResponse(
            consumed=detail is not None,
            detail=detail,
        )

