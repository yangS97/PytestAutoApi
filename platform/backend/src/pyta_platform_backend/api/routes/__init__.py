"""按业务拆分的路由模块。"""

from pyta_platform_backend.api.routes.dashboard import create_dashboard_router
from pyta_platform_backend.api.routes.demo_suites import create_demo_suites_router
from pyta_platform_backend.api.routes.health import create_health_router
from pyta_platform_backend.api.routes.management import create_management_router
from pyta_platform_backend.api.routes.runs import create_runs_router
from pyta_platform_backend.api.routes.worker import create_worker_router

__all__ = [
    "create_dashboard_router",
    "create_demo_suites_router",
    "create_health_router",
    "create_management_router",
    "create_runs_router",
    "create_worker_router",
]
