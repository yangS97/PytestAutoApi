"""健康检查路由。"""

from fastapi import APIRouter, status

from pyta_platform_backend.config import BackendSettings
from pyta_platform_backend.schemas.health import HealthResponse


def create_health_router(settings: BackendSettings) -> APIRouter:
    """注册健康检查接口。"""

    router = APIRouter(prefix="/health", tags=["health"])

    @router.get("/live", response_model=HealthResponse, status_code=status.HTTP_200_OK)
    def live() -> HealthResponse:
        """最小健康检查。

        这里只回答“API 进程是否活着，以及当前绑定了什么环境配置”，
        不在这里顺带探测 worker、数据库或外部系统，避免把简单探针做成重操作。
        """

        return HealthResponse(
            status="ok",
            service=settings.app_name,
            environment=settings.app_env,
        )

    return router
