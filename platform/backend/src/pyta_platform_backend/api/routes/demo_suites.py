"""样例套件接口。"""

from fastapi import APIRouter, status

from pyta_platform_backend.schemas.demo_suite import (
    CreateDemoSuiteRunRequest,
    CreateDemoSuiteRunResponse,
    ListDemoSuitesResponse,
)
from pyta_platform_backend.services.demo_suite_service import DemoSuiteService


def create_demo_suites_router(demo_suite_service: DemoSuiteService) -> APIRouter:
    """注册样例套件接口。"""

    router = APIRouter(prefix="/demo-suites", tags=["demo-suites"])

    @router.get("", response_model=ListDemoSuitesResponse, status_code=status.HTTP_200_OK)
    def list_demo_suites() -> ListDemoSuitesResponse:
        """列出当前可验证的迁移样例套件。"""

        return demo_suite_service.list_suites()

    @router.post(
        "/{suite_id}/runs",
        response_model=CreateDemoSuiteRunResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_demo_suite_run(
        suite_id: str,
        payload: CreateDemoSuiteRunRequest,
    ) -> CreateDemoSuiteRunResponse:
        """从样例套件创建 run。"""

        return demo_suite_service.create_run_from_suite(suite_id=suite_id, request=payload)

    return router

