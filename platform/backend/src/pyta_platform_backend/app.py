"""FastAPI 应用装配入口。"""

from fastapi import FastAPI

from pyta_platform_backend.api.router import register_routes
from pyta_platform_backend.config import BackendSettings
from pyta_platform_backend.repositories.management_repository import InMemoryManagementRepository
from pyta_platform_backend.repositories.run_repository import InMemoryRunRepository
from pyta_platform_backend.scheduler.lightweight_scheduler import LightweightScheduler
from pyta_platform_backend.services.dashboard_service import DashboardService
from pyta_platform_backend.services.demo_suite_service import DemoSuiteService
from pyta_platform_backend.services.management_service import ManagementService
from pyta_platform_backend.services.run_service import RunService
from pyta_platform_backend.services.worker_control_service import WorkerControlService
from pyta_platform_backend.workers.dispatcher import MemoryRunDispatcher
from pyta_platform_backend.workers.runner import MemoryWorkerRunner


def build_default_run_service(
    settings: BackendSettings,
    management_repository: InMemoryManagementRepository = None,
) -> RunService:
    """组装默认的 run service。

    这里明确体现第一阶段的边界：
    - API 进程只负责“写入平台主真源” + “投递给 worker”
    - 真正的长任务执行不发生在 FastAPI 路由里
    """

    repository = InMemoryRunRepository()
    dispatcher = MemoryRunDispatcher(channel_name=settings.run_dispatch_channel)
    return RunService(
        repository=repository,
        dispatcher=dispatcher,
        management_repository=management_repository,
    )


def create_app(
    settings: BackendSettings = None,
    run_service: RunService = None,
    scheduler: LightweightScheduler = None,
) -> FastAPI:
    """创建 FastAPI 应用实例。

    通过显式注入 ``settings`` / ``run_service`` / ``scheduler``，
    可以让测试、未来的依赖替换和真实部署装配都保持清晰。
    """

    resolved_settings = settings or BackendSettings.from_env()
    shared_management_repository = InMemoryManagementRepository()
    resolved_run_service = run_service or build_default_run_service(
        resolved_settings,
        management_repository=shared_management_repository,
    )
    resolved_scheduler = scheduler or LightweightScheduler(
        poll_interval_seconds=resolved_settings.scheduler_poll_interval_seconds
    )
    resolved_dashboard_service = DashboardService(repository=resolved_run_service.repository)
    resolved_demo_suite_service = DemoSuiteService(
        run_service=resolved_run_service,
        management_repository=shared_management_repository,
    )
    resolved_management_service = ManagementService(
        repository=shared_management_repository,
        run_repository=resolved_run_service.repository,
    )
    resolved_worker_runner = MemoryWorkerRunner(
        dispatcher=resolved_run_service.dispatcher,
        run_service=resolved_run_service,
    )
    resolved_worker_control_service = WorkerControlService(worker_runner=resolved_worker_runner)

    app = FastAPI(
        title=resolved_settings.app_name,
        debug=resolved_settings.debug,
        version=resolved_settings.app_version,
    )

    # 把核心对象挂到 app.state，方便后续在启动事件、管理接口或测试里复用。
    app.state.settings = resolved_settings
    app.state.run_service = resolved_run_service
    app.state.scheduler = resolved_scheduler
    app.state.dashboard_service = resolved_dashboard_service
    app.state.demo_suite_service = resolved_demo_suite_service
    app.state.management_service = resolved_management_service
    app.state.worker_runner = resolved_worker_runner
    app.state.worker_control_service = resolved_worker_control_service

    register_routes(
        app=app,
        settings=resolved_settings,
        run_service=resolved_run_service,
        dashboard_service=resolved_dashboard_service,
        demo_suite_service=resolved_demo_suite_service,
        management_service=resolved_management_service,
        worker_control_service=resolved_worker_control_service,
    )
    return app
