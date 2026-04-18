"""演示/迁移样例套件服务。

这里的目标不是把旧 YAML 原样搬到平台里，而是把其中两组最关键的历史能力
重新表达成新框架的标准模型：

1. 登录鉴权
2. 培训对练 - 人设库管理

这样用户后续验证时，看到的是“新框架如何表达这些能力”，
而不是“把旧文件换个入口继续跑”。
"""

from dataclasses import dataclass
from hashlib import md5
from pathlib import Path
from typing import Optional

import yaml
from fastapi import HTTPException, status

from pyta_platform_backend.repositories.management_repository import InMemoryManagementRepository
from pyta_platform_backend.schemas.demo_suite import (
    CreateDemoSuiteRunRequest,
    CreateDemoSuiteRunResponse,
    DemoSuiteSummaryResponse,
    ListDemoSuitesResponse,
)
from pyta_platform_backend.schemas.run import CreateRunRequest
from pyta_platform_backend.services.run_service import RunService
from testflow_engine import (
    AssertionOperator,
    AssertionSource,
    AssertionSpec,
    BodyType,
    ExtractionSource,
    ExtractionSpec,
    HttpMethod,
    RequestSpec,
    TestCaseDefinition,
    TestRunDefinition,
)


@dataclass(frozen=True)
class DemoSuiteDefinition:
    """后端内部使用的样例套件定义。"""

    suite_id: str
    title: str
    description: str
    source: str
    run_definition: TestRunDefinition
    supports_live_http: bool = True
    mock_case_responses: dict[str, dict[str, object]] = None


class DemoSuiteService:
    """管理样例套件目录，并负责把它们转换成 run 创建请求。"""

    def __init__(
        self,
        run_service: RunService,
        management_repository: Optional[InMemoryManagementRepository] = None,
    ) -> None:
        self._run_service = run_service
        self._management_repository = management_repository
        self._default_host = self._load_default_host()
        self._suites = self._build_demo_suites()

    def list_suites(self) -> ListDemoSuitesResponse:
        """列出当前可验证的样例套件。"""

        return ListDemoSuitesResponse(
            items=[
                DemoSuiteSummaryResponse(
                    suite_id=item.suite_id,
                    title=item.title,
                    description=item.description,
                    source=item.source,
                    case_count=len(item.run_definition.cases),
                    supports_live_http=item.supports_live_http,
                )
                for item in self._suites.values()
            ]
        )

    def create_run_from_suite(
        self,
        suite_id: str,
        request: CreateDemoSuiteRunRequest,
    ) -> CreateDemoSuiteRunResponse:
        """把样例套件提交为平台 run。"""

        suite = self._get_suite(suite_id)
        host = self._resolve_host_for_run(request)
        transport_mode = "mock" if request.mode.strip().lower() == "mock" else "live"

        run_definition = self._copy_run_with_variables(
            suite.run_definition,
            variables=self._build_variables_for_suite(suite_id=suite_id, host=host),
        )
        run_payload = {
            "execution_mode": "standard_run",
            "transport_mode": transport_mode,
            "run_definition": self._dump_model(run_definition),
        }
        if transport_mode == "mock":
            run_payload["mock_case_responses"] = dict(suite.mock_case_responses or {})

        response = self._run_service.create_run(
            CreateRunRequest(
                suite_id=suite.suite_id,
                environment_id=request.environment_id,
                trigger_source="demo-suite",
                requested_by=request.requested_by,
                payload=run_payload,
            )
        )
        return CreateDemoSuiteRunResponse(
            run_id=response.run_id,
            status=response.status,
            dispatch_channel=response.dispatch_channel,
            environment_id=response.environment_id,
            environment_name=response.environment_name,
            suite_id=suite.suite_id,
            mode=transport_mode,
        )

    def _resolve_host_for_run(self, request: CreateDemoSuiteRunRequest) -> str:
        """为 demo run 解析最终 host。"""

        if request.host_override:
            return request.host_override.rstrip("/")

        if request.environment_id and self._management_repository is not None:
            environment = self._management_repository.get_environment_by_id(request.environment_id)
            if environment is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"environment 不存在: {request.environment_id}",
                )
            return environment.base_url

        return self._default_host

    def _get_suite(self, suite_id: str) -> DemoSuiteDefinition:
        """读取指定样例套件。"""

        try:
            return self._suites[suite_id]
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未知样例套件: {suite_id}",
            ) from exc

    def _build_demo_suites(self) -> dict[str, DemoSuiteDefinition]:
        """构造当前两组演示套件。"""

        login_suite = self._build_login_suite()
        persona_suite = self._build_persona_suite()
        return {
            login_suite.suite_id: login_suite,
            persona_suite.suite_id: persona_suite,
        }

    def _build_login_suite(self) -> DemoSuiteDefinition:
        """构建登录鉴权样例套件。"""

        cases = [
            TestCaseDefinition(
                case_id="login_success",
                title="正常登录",
                request=RequestSpec(
                    method=HttpMethod.POST,
                    url="{{host}}/api/v1/user/password_login",
                    headers={"Content-Type": "application/json"},
                    body_type=BodyType.JSON,
                    body={
                        "username": "13300000009",
                        "password": self._login_password_md5(),
                        "captchaId": "",
                        "captcha": "",
                    },
                ),
                assertions=[
                    AssertionSpec(
                        name="http-status",
                        source=AssertionSource.STATUS_CODE,
                        operator=AssertionOperator.EQUALS,
                        expected=200,
                    ),
                    AssertionSpec(
                        name="business-code",
                        selector="code",
                        operator=AssertionOperator.EQUALS,
                        expected=200,
                    ),
                    AssertionSpec(
                        name="token-exists",
                        selector="data.token",
                        operator=AssertionOperator.EXISTS,
                    ),
                ],
                extractors=[
                    ExtractionSpec(
                        name="cache-auth-token",
                        selector="data.token",
                        source=ExtractionSource.RESPONSE_BODY,
                        target="cache.auth_token",
                    )
                ],
                description="新框架标准化表达的登录成功用例。",
            ),
            TestCaseDefinition(
                case_id="login_wrong_password",
                title="密码错误",
                request=RequestSpec(
                    method=HttpMethod.POST,
                    url="{{host}}/api/v1/user/password_login",
                    headers={"Content-Type": "application/json"},
                    body_type=BodyType.JSON,
                    body={
                        "username": "13300000009",
                        "password": "wrong_md5_hash",
                        "captchaId": "",
                        "captcha": "",
                    },
                ),
                assertions=[
                    AssertionSpec(
                        name="http-status",
                        source=AssertionSource.STATUS_CODE,
                        operator=AssertionOperator.EQUALS,
                        expected=200,
                    ),
                    AssertionSpec(
                        name="business-code",
                        selector="code",
                        operator=AssertionOperator.EQUALS,
                        expected=500,
                    ),
                ],
                description="新框架标准化表达的密码错误用例。",
            ),
            TestCaseDefinition(
                case_id="login_empty_password",
                title="密码为空",
                request=RequestSpec(
                    method=HttpMethod.POST,
                    url="{{host}}/api/v1/user/password_login",
                    headers={"Content-Type": "application/json"},
                    body_type=BodyType.JSON,
                    body={
                        "username": "13300000009",
                        "password": None,
                        "captchaId": "",
                        "captcha": "",
                    },
                ),
                assertions=[
                    AssertionSpec(
                        name="http-status",
                        source=AssertionSource.STATUS_CODE,
                        operator=AssertionOperator.EQUALS,
                        expected=200,
                    ),
                    AssertionSpec(
                        name="business-code",
                        selector="code",
                        operator=AssertionOperator.EQUALS,
                        expected=500,
                    ),
                ],
                description="新框架标准化表达的密码为空用例。",
            ),
        ]
        return DemoSuiteDefinition(
            suite_id="demo-login-auth",
            title="登录鉴权",
            description="从历史登录 YAML 提炼出的新框架标准化套件。",
            source="legacy-login",
            run_definition=TestRunDefinition(name="demo-login-auth", cases=cases),
            mock_case_responses={
                "login_success": {
                    "status_code": 200,
                    "body": {"code": 200, "data": {"token": "mock-token"}},
                    "headers": {"content-type": "application/json"},
                },
                "login_wrong_password": {
                    "status_code": 200,
                    "body": {"code": 500},
                    "headers": {"content-type": "application/json"},
                },
                "login_empty_password": {
                    "status_code": 200,
                    "body": {"code": 500},
                    "headers": {"content-type": "application/json"},
                },
            },
        )

    def _build_persona_suite(self) -> DemoSuiteDefinition:
        """构建培训对练 - 人设库管理样例套件。"""

        cases = [
            TestCaseDefinition(
                case_id="persona_person_page",
                title="查询人设分页列表",
                request=RequestSpec(
                    method=HttpMethod.GET,
                    url="{{host}}/api/v1/practice/person/page?pageNum=1&pageSize=10&personaType=&enable=&searchName=",
                    headers={"Content-Type": "application/json"},
                    body_type=BodyType.NONE,
                ),
                assertions=[self._code_assert(200)],
                extractors=[
                    ExtractionSpec(
                        name="cache-persona-id",
                        selector="data.records.0.id",
                        target="cache.persona_id",
                    )
                ],
                description="查询人设列表，并把第一条人设 ID 写入 cache。",
            ),
            TestCaseDefinition(
                case_id="persona_evaluate_page",
                title="获取可选评估包列表",
                request=RequestSpec(
                    method=HttpMethod.POST,
                    url="{{host}}/api/v1/practice/persona/consultation_evaluate_page",
                    headers={"Content-Type": "application/json"},
                    body_type=BodyType.JSON,
                    body={"id": ""},
                ),
                assertions=[self._code_assert(200)],
                extractors=[
                    ExtractionSpec(
                        name="cache-evaluate-package-id",
                        selector="data.0.id",
                        target="cache.evaluate_pkg_id",
                    )
                ],
                description="查询评估包列表，并把第一个评估包 ID 写入 cache。",
            ),
            TestCaseDefinition(
                case_id="persona_chapter_list",
                title="预览评估包章节详情",
                request=RequestSpec(
                    method=HttpMethod.GET,
                    url="{{host}}/api/v1/consultation_evaluate/chapter_list?id={{cache.evaluate_pkg_id}}",
                    headers={"Content-Type": "application/json"},
                    body_type=BodyType.NONE,
                ),
                assertions=[self._code_assert(200)],
                description="使用前一步缓存的评估包 ID 获取章节详情。",
            ),
            TestCaseDefinition(
                case_id="persona_bind_package",
                title="给指定人设绑定评估包",
                request=RequestSpec(
                    method=HttpMethod.POST,
                    url="{{host}}/api/v1/practice/persona/consultation_evaluate_select",
                    headers={"Content-Type": "application/json"},
                    body_type=BodyType.JSON,
                    body={
                        "evaluationPackageId": "{{cache.evaluate_pkg_id}}",
                        "id": "{{cache.persona_id}}",
                    },
                ),
                assertions=[self._code_assert(200)],
                description="使用 cache 中的人设 ID 和评估包 ID 执行绑定。",
            ),
            TestCaseDefinition(
                case_id="persona_verify_refresh",
                title="验证绑定后人设列表刷新",
                request=RequestSpec(
                    method=HttpMethod.GET,
                    url="{{host}}/api/v1/practice/person/page?pageNum=1&pageSize=10&personaType=&enable=&searchName=",
                    headers={"Content-Type": "application/json"},
                    body_type=BodyType.NONE,
                ),
                assertions=[self._code_assert(200)],
                description="绑定后再次查询列表，验证主链路可继续执行。",
            ),
            TestCaseDefinition(
                case_id="persona_filter_type",
                title="按类型筛选人设",
                request=RequestSpec(
                    method=HttpMethod.GET,
                    url="{{host}}/api/v1/practice/person/page?pageNum=1&pageSize=10&personaType=1&enable=true&searchName=",
                    headers={"Content-Type": "application/json"},
                    body_type=BodyType.NONE,
                ),
                assertions=[self._code_assert(200)],
                description="按类型筛选人设，验证查询链路稳定。",
            ),
        ]
        return DemoSuiteDefinition(
            suite_id="demo-persona-library",
            title="培训对练 - 人设库管理",
            description="从历史人设库管理流程中提炼出的新框架标准化套件。",
            source="legacy-practice-persona",
            run_definition=TestRunDefinition(name="demo-persona-library", cases=cases),
            mock_case_responses={
                "persona_person_page": {
                    "status_code": 200,
                    "body": {"code": 200, "data": {"records": [{"id": "persona-001"}]}},
                    "headers": {"content-type": "application/json"},
                },
                "persona_evaluate_page": {
                    "status_code": 200,
                    "body": {"code": 200, "data": [{"id": "pkg-001"}]},
                    "headers": {"content-type": "application/json"},
                },
                "persona_chapter_list": {
                    "status_code": 200,
                    "body": {"code": 200, "data": []},
                    "headers": {"content-type": "application/json"},
                },
                "persona_bind_package": {
                    "status_code": 200,
                    "body": {"code": 200},
                    "headers": {"content-type": "application/json"},
                },
                "persona_verify_refresh": {
                    "status_code": 200,
                    "body": {"code": 200, "data": {"records": [{"id": "persona-001"}]}},
                    "headers": {"content-type": "application/json"},
                },
                "persona_filter_type": {
                    "status_code": 200,
                    "body": {"code": 200, "data": {"records": []}},
                    "headers": {"content-type": "application/json"},
                },
            },
        )

    @staticmethod
    def _code_assert(expected: int) -> AssertionSpec:
        """生成最常见的 code 断言。"""

        return AssertionSpec(
            name="business-code",
            selector="code",
            operator=AssertionOperator.EQUALS,
            expected=expected,
        )

    def _build_variables_for_suite(self, suite_id: str, host: str) -> dict[str, object]:
        """为样例套件构造运行时变量。"""

        variables: dict[str, object] = {"host": host}
        if suite_id == "demo-persona-library":
            variables["auth_bootstrap"] = {
                "login_url": f"{host.rstrip('/')}/api/v1/user/password_login",
                "request_mode": "json",
                "headers": {"Content-Type": "application/json"},
                "body": {
                    "username": "13300000009",
                    "password": self._login_password_md5(),
                    "captchaId": "",
                    "captcha": "",
                },
                "token_path": "data.token",
                "token_cache_key": "auth_token",
                "header_name": "Authorization",
                "header_template": "{token}",
            }
        return variables

    @staticmethod
    def _copy_run_with_variables(
        run_definition: TestRunDefinition,
        variables: dict[str, object],
    ) -> TestRunDefinition:
        """为本次执行复制 run，并注入运行时变量。"""

        if hasattr(run_definition, "model_copy"):
            return run_definition.model_copy(update={"variables": variables}, deep=True)
        return run_definition.copy(update={"variables": variables}, deep=True)

    @staticmethod
    def _dump_model(model) -> dict[str, object]:
        """兼容 Pydantic v1/v2 的 dump。"""

        if hasattr(model, "model_dump"):
            return model.model_dump()
        return model.dict()

    @staticmethod
    def _login_password_md5() -> str:
        """复用旧登录逻辑中的密码哈希。"""

        return md5(b"yanji2026!").hexdigest()

    @staticmethod
    def _load_default_host() -> str:
        """从旧配置中读取默认 host，便于迁移验证。"""

        root = Path(__file__).resolve().parents[5]
        config_path = root / "common" / "config.yaml"
        if not config_path.exists():
            return "https://api-test.yanjiai.com"

        with config_path.open("r", encoding="utf-8") as file:
            payload = yaml.safe_load(file) or {}
        return str(payload.get("host") or "https://api-test.yanjiai.com").rstrip("/")
