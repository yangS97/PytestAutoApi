"""run 相关接口。"""

from fastapi import APIRouter, status

from pyta_platform_backend.schemas.run import (
    CreateRunRequest,
    CreateRunResponse,
    ListRunsResponse,
    RunDetailResponse,
    UpdateRunStatusRequest,
)
from pyta_platform_backend.services.run_service import RunService


def create_runs_router(run_service: RunService) -> APIRouter:
    """注册 run 路由。

    这里故意只放“创建 run”入口，用来体现平台的第一阶段职责：
    API 收到请求后创建 run 记录，并把执行任务交给 worker。
    """

    router = APIRouter(prefix="/runs", tags=["runs"])

    @router.post("", response_model=CreateRunResponse, status_code=status.HTTP_202_ACCEPTED)
    def create_run(payload: CreateRunRequest) -> CreateRunResponse:
        """创建 run 并投递到 worker。"""

        return run_service.create_run(payload)

    @router.get("", response_model=ListRunsResponse, status_code=status.HTTP_200_OK)
    def list_runs(limit: int = 20, offset: int = 0) -> ListRunsResponse:
        """返回 run 列表。

        这里优先给结果页和仪表盘提供真实数据来源。
        """

        return run_service.list_runs(limit=limit, offset=offset)

    @router.get("/{run_id}", response_model=RunDetailResponse, status_code=status.HTTP_200_OK)
    def get_run_detail(run_id: str) -> RunDetailResponse:
        """返回单个 run 详情。"""

        return run_service.get_run_detail(run_id)

    @router.patch(
        "/{run_id}/status",
        response_model=RunDetailResponse,
        status_code=status.HTTP_200_OK,
    )
    def update_run_status(run_id: str, payload: UpdateRunStatusRequest) -> RunDetailResponse:
        """更新 run 状态。

        这个接口主要给 worker 或调度器回写状态使用。
        """

        return run_service.update_run_status(run_id=run_id, payload=payload)

    return router
