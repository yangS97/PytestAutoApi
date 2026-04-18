"""仪表盘相关接口。"""

from fastapi import APIRouter, status

from pyta_platform_backend.schemas.dashboard import DashboardOverviewResponse
from pyta_platform_backend.services.dashboard_service import DashboardService


def create_dashboard_router(dashboard_service: DashboardService) -> APIRouter:
    """注册首页总览接口。"""

    router = APIRouter(prefix="/dashboard", tags=["dashboard"])

    @router.get(
        "/overview",
        response_model=DashboardOverviewResponse,
        status_code=status.HTTP_200_OK,
    )
    def get_overview() -> DashboardOverviewResponse:
        """返回首页最小总览。

        这里优先服务前端首页，不把接口做成一个“万能统计中心”。
        """

        return dashboard_service.get_overview()

    return router
