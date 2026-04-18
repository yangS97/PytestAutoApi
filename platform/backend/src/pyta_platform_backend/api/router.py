"""统一注册 API 路由。"""

from fastapi import APIRouter, FastAPI

from pyta_platform_backend.api.routes.dashboard import create_dashboard_router
from pyta_platform_backend.api.routes.demo_suites import create_demo_suites_router
from pyta_platform_backend.api.routes.health import create_health_router
from pyta_platform_backend.api.routes.management import create_management_router
from pyta_platform_backend.api.routes.runs import create_runs_router
from pyta_platform_backend.api.routes.worker import create_worker_router
from pyta_platform_backend.config import BackendSettings
from pyta_platform_backend.services.dashboard_service import DashboardService
from pyta_platform_backend.services.demo_suite_service import DemoSuiteService
from pyta_platform_backend.services.management_service import ManagementService
from pyta_platform_backend.services.run_service import RunService
from pyta_platform_backend.services.worker_control_service import WorkerControlService


def build_api_router(
    settings: BackendSettings,
    run_service: RunService,
    dashboard_service: DashboardService,
    demo_suite_service: DemoSuiteService,
    management_service: ManagementService,
    worker_control_service: WorkerControlService,
) -> APIRouter:
    """构建平台 API 根路由。"""

    router = APIRouter(prefix=settings.api_prefix)
    router.include_router(create_dashboard_router(dashboard_service))
    router.include_router(create_demo_suites_router(demo_suite_service))
    router.include_router(create_health_router(settings))
    router.include_router(create_management_router(management_service))
    router.include_router(create_runs_router(run_service))
    router.include_router(create_worker_router(worker_control_service))
    return router


def register_routes(
    app: FastAPI,
    settings: BackendSettings,
    run_service: RunService,
    dashboard_service: DashboardService,
    demo_suite_service: DemoSuiteService,
    management_service: ManagementService,
    worker_control_service: WorkerControlService,
) -> None:
    """把所有业务路由注册到 FastAPI app。"""

    app.include_router(
        build_api_router(
            settings=settings,
            run_service=run_service,
            dashboard_service=dashboard_service,
            demo_suite_service=demo_suite_service,
            management_service=management_service,
            worker_control_service=worker_control_service,
        )
    )
