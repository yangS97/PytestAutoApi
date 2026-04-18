"""run 业务服务层。"""

from copy import deepcopy
from typing import Optional

from fastapi import HTTPException, status

from pyta_platform_backend.repositories.management_repository import InMemoryManagementRepository
from pyta_platform_backend.repositories.run_repository import InMemoryRunRepository, RunRecord
from pyta_platform_backend.schemas.run import (
    CreateRunRequest,
    CreateRunResponse,
    ListRunsResponse,
    RunDetailResponse,
    UpdateRunStatusRequest,
)
from pyta_platform_backend.workers.dispatcher import DispatchTask, MemoryRunDispatcher


class RunService:
    """run 服务。

    服务层负责串联“平台真源持久化”和“向 worker 投递任务”两个步骤。
    这样路由函数就能保持很薄，后续替换数据库或消息投递实现时也不会改 API 层。
    """

    def __init__(
        self,
        repository: InMemoryRunRepository,
        dispatcher: MemoryRunDispatcher,
        management_repository: Optional[InMemoryManagementRepository] = None,
    ) -> None:
        self._repository = repository
        self._dispatcher = dispatcher
        self._management_repository = management_repository

    @property
    def repository(self) -> InMemoryRunRepository:
        """暴露仓储给测试或诊断代码读取。"""

        return self._repository

    @property
    def dispatcher(self) -> MemoryRunDispatcher:
        """暴露投递器给测试或诊断代码读取。"""

        return self._dispatcher

    def create_run(self, payload: CreateRunRequest) -> CreateRunResponse:
        """创建 run 并投递到 worker。"""

        environment = self._resolve_environment(payload.environment_id)
        prepared_payload = self._prepare_run_request(payload, environment=environment)
        record: RunRecord = self._repository.create_pending_run(
            prepared_payload,
            environment_name=environment.name if environment else None,
        )
        self._dispatcher.dispatch(
            DispatchTask(
                run_id=record.run_id,
                suite_id=record.suite_id,
                trigger_source=record.trigger_source,
                requested_by=record.requested_by,
                payload=record.payload,
                dispatched_at=record.created_at,
            )
        )
        return CreateRunResponse(
            run_id=record.run_id,
            status=record.status,
            dispatch_channel=self._dispatcher.channel_name,
            environment_id=record.environment_id,
            environment_name=record.environment_name,
        )

    def list_runs(self, limit: int = 20, offset: int = 0) -> ListRunsResponse:
        """列出 run 列表。"""

        safe_limit = max(1, min(limit, 200))
        safe_offset = max(0, offset)
        return self._repository.list_runs(limit=safe_limit, offset=safe_offset)

    def get_run_detail(self, run_id: str) -> RunDetailResponse:
        """按 run_id 查询详情。"""

        detail = self._repository.get_detail(run_id)
        if detail is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"run 不存在: {run_id}",
            )
        return detail

    def update_run_status(self, run_id: str, payload: UpdateRunStatusRequest) -> RunDetailResponse:
        """更新 run 状态。"""

        detail = self._repository.update_status(run_id=run_id, payload=payload)
        if detail is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"run 不存在: {run_id}",
            )
        return detail

    def _resolve_environment(self, environment_id: Optional[str]):
        """解析 environment_id，并返回对应环境记录。"""

        if not environment_id:
            return None
        if self._management_repository is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前 run service 未接入 environment 仓储，无法解析 environment_id",
            )

        environment = self._management_repository.get_environment_by_id(environment_id)
        if environment is not None:
            return environment

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"environment 不存在: {environment_id}",
        )

    @staticmethod
    def _prepare_run_request(
        payload: CreateRunRequest,
        *,
        environment,
    ) -> CreateRunRequest:
        """把 environment 快照写入运行时 payload。"""

        runtime_payload = deepcopy(payload.payload)
        if environment is not None:
            runtime_payload["environment"] = {
                "id": environment.id,
                "name": environment.name,
                "base_url": environment.base_url,
                "auth_mode": environment.auth_mode,
                "variables": deepcopy(environment.variables),
            }

        if hasattr(payload, "model_copy"):
            return payload.model_copy(update={"payload": runtime_payload}, deep=True)
        return payload.copy(update={"payload": runtime_payload}, deep=True)
