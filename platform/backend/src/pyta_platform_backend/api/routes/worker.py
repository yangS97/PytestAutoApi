"""worker 本地控制接口。"""

from fastapi import APIRouter, status

from pyta_platform_backend.schemas.run import RunDetailResponse
from pyta_platform_backend.schemas.worker import RunNextResponse
from pyta_platform_backend.services.worker_control_service import WorkerControlService


def create_worker_router(worker_control_service: WorkerControlService) -> APIRouter:
    """注册本地 worker 控制接口。"""

    router = APIRouter(prefix="/worker", tags=["worker"])

    @router.post("/run-next", response_model=RunNextResponse, status_code=status.HTTP_200_OK)
    def run_next() -> RunNextResponse:
        """消费一条排队中的任务。

        这个接口的定位很窄：
        - 方便本地验证样例套件
        - 方便演示“队列 -> worker -> 状态回写”链路
        - 不代表最终生产环境一定暴露这种接口
        """

        return worker_control_service.run_next()

    @router.post(
        "/runs/{run_id}/execute",
        response_model=RunDetailResponse,
        status_code=status.HTTP_200_OK,
    )
    def run_by_id(run_id: str) -> RunDetailResponse:
        """立即执行指定 run_id。

        这个入口专门服务单人工作台的一键运行：
        页面创建完 run 后，不必再赌 FIFO 队列，而是直接执行这次点击对应的任务。
        """

        return worker_control_service.run_by_id(run_id)

    return router
