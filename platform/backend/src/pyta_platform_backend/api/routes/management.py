"""平台管理目录接口。"""

from fastapi import APIRouter, status

from pyta_platform_backend.schemas.management import (
    CaseSummaryResponse,
    CreateEnvironmentRequest,
    CreateEnvironmentResponse,
    DeleteEnvironmentResponse,
    EnvironmentDetailResponse,
    EnvironmentSummaryResponse,
    ScheduleSummaryResponse,
    SuiteSummaryResponse,
    UpdateEnvironmentRequest,
    UpdateEnvironmentResponse,
)
from pyta_platform_backend.services.management_service import ManagementService


def create_management_router(management_service: ManagementService) -> APIRouter:
    """注册管理页最小目录接口。"""

    router = APIRouter(tags=["management"])

    @router.get("/cases", response_model=list[CaseSummaryResponse], status_code=status.HTTP_200_OK)
    def list_cases() -> list[CaseSummaryResponse]:
        """返回用例目录最小摘要。"""

        return management_service.list_cases()

    @router.get(
        "/suites",
        response_model=list[SuiteSummaryResponse],
        status_code=status.HTTP_200_OK,
    )
    def list_suites() -> list[SuiteSummaryResponse]:
        """返回套件目录最小摘要。"""

        return management_service.list_suites()

    @router.get(
        "/environments",
        response_model=list[EnvironmentSummaryResponse],
        status_code=status.HTTP_200_OK,
    )
    def list_environments() -> list[EnvironmentSummaryResponse]:
        """返回环境目录最小摘要。"""

        return management_service.list_environments()

    @router.get(
        "/environments/{environment_id}",
        response_model=EnvironmentDetailResponse,
        status_code=status.HTTP_200_OK,
    )
    def get_environment_detail(environment_id: str) -> EnvironmentDetailResponse:
        """返回单个环境详情。"""

        return management_service.get_environment_detail(environment_id)

    @router.post(
        "/environments",
        response_model=CreateEnvironmentResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_environment(payload: CreateEnvironmentRequest) -> CreateEnvironmentResponse:
        """创建新的环境目录。"""

        return management_service.create_environment(payload)

    @router.patch(
        "/environments/{environment_id}",
        response_model=UpdateEnvironmentResponse,
        status_code=status.HTTP_200_OK,
    )
    def update_environment(
        environment_id: str,
        payload: UpdateEnvironmentRequest,
    ) -> UpdateEnvironmentResponse:
        """更新环境目录。"""

        return management_service.update_environment(environment_id, payload)

    @router.delete(
        "/environments/{environment_id}",
        response_model=DeleteEnvironmentResponse,
        status_code=status.HTTP_200_OK,
    )
    def delete_environment(environment_id: str) -> DeleteEnvironmentResponse:
        """删除环境目录。"""

        return management_service.delete_environment(environment_id)

    @router.get(
        "/schedules",
        response_model=list[ScheduleSummaryResponse],
        status_code=status.HTTP_200_OK,
    )
    def list_schedules() -> list[ScheduleSummaryResponse]:
        """返回调度目录最小摘要。"""

        return management_service.list_schedules()

    return router
