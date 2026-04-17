"""run 业务服务层。"""

from fastapi import HTTPException, status

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
    ) -> None:
        self._repository = repository
        self._dispatcher = dispatcher

    @property
    def repository(self) -> InMemoryRunRepository:
        """暴露仓储给测试或诊断代码读取。"""

        return self._repository

    @property
    def dispatcher(self) -> MemoryRunDispatcher:
        """暴露投递器给测试或诊断代码读取。"""

        return self._dispatcher

    def create_run(self, payload: CreateRunRequest) -> CreateRunResponse:
        """创建 run 并投递到 worker。

        这里不做任何长任务执行，只把必要信息整理好后交给 dispatcher。
        """

        record: RunRecord = self._repository.create_pending_run(payload)
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
                detail="run 不存在: %s" % run_id,
            )
        return detail

    def update_run_status(self, run_id: str, payload: UpdateRunStatusRequest) -> RunDetailResponse:
        """更新 run 状态。

        第一阶段的状态流转保持宽松，只做“有记录才允许更新”的最小规则。
        等 worker 真正接起来后，再补更严格的状态机校验。
        """

        detail = self._repository.update_status(run_id=run_id, payload=payload)
        if detail is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="run 不存在: %s" % run_id,
            )
        return detail
