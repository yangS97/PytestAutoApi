"""worker 本地控制服务。"""

from fastapi import HTTPException, status

from pyta_platform_backend.schemas.run import RunDetailResponse
from pyta_platform_backend.schemas.worker import RunNextResponse
from pyta_platform_backend.services.run_service import RunService


class WorkerControlService:
    """给本地开发提供一个最小的 worker 控制入口。"""

    def __init__(self, worker_runner, run_service: RunService) -> None:
        self._worker_runner = worker_runner
        self._run_service = run_service

    def run_next(self) -> RunNextResponse:
        """消费一条排队中的任务。"""

        detail = self._worker_runner.run_next()
        return RunNextResponse(
            consumed=detail is not None,
            detail=detail,
        )

    def run_by_id(self, run_id: str) -> RunDetailResponse:
        """消费指定 run_id 的待执行任务。"""

        detail = self._worker_runner.run_by_id(run_id)
        if detail is not None:
            return detail

        if self._run_service.repository.get_by_id(run_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"run 不存在: {run_id}",
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"run 当前不在待执行队列中: {run_id}",
        )
