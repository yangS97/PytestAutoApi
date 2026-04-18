import httpx

from testflow_engine import (
    AssertionOperator,
    AssertionSpec,
    BodyType,
    BootstrapAuthPlugin,
    CallableTransport,
    ExtractionSource,
    ExtractionSpec,
    HttpMethod,
    RequestSpec,
    ResponseSnapshot,
)
from testflow_engine import (
    TestCaseDefinition as CaseDefinition,
)
from testflow_engine import (
    TestFlowEngine as FlowEngine,
)
from testflow_engine import (
    TestRunDefinition as RunDefinition,
)


def test_standard_run_can_use_bootstrap_auth_and_extractors_together():
    """新框架标准 run 应能同时支持登录 bootstrap 和变量提取。

    这个测试验证的是“新设计方向是否成立”：
    - token 通过插件拿到
    - request header 自动注入
    - 提取器把响应值写回 context
    """

    def login_handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://example.test/api/v1/user/password_login"
        return httpx.Response(
            200,
            json={"data": {"token": "real-token-001"}},
            headers={"content-type": "application/json"},
        )

    auth_plugin = BootstrapAuthPlugin(
        http_client=httpx.Client(transport=httpx.MockTransport(login_handler))
    )

    seen_headers = {}

    def business_transport(request, context, case):
        seen_headers[case.case_id] = dict(request.headers)
        if case.case_id == "list-persona":
            return ResponseSnapshot(
                status_code=200,
                body={"code": 200, "data": {"records": [{"id": "persona-001"}]}},
            )
        return ResponseSnapshot(
            status_code=200,
            body={"code": 200, "message": "ok"},
        )

    run = RunDefinition(
        name="standard-persona-demo",
        variables={
            "host": "https://example.test",
            "auth_bootstrap": {
                "login_url": "https://example.test/api/v1/user/password_login",
                "request_mode": "json",
                "headers": {"Content-Type": "application/json"},
                "body": {
                    "username": "13300000009",
                    "password": "md5-password",
                    "captchaId": "",
                    "captcha": "",
                },
                "token_path": "data.token",
                "token_cache_key": "auth_token",
                "header_name": "Authorization",
                "header_template": "{token}",
            },
        },
        cases=[
            CaseDefinition(
                case_id="list-persona",
                title="查询人设列表",
                request=RequestSpec(
                    method=HttpMethod.GET,
                    url="{{host}}/api/v1/practice/person/page?pageNum=1",
                    headers={"Content-Type": "application/json"},
                    body_type=BodyType.NONE,
                ),
                assertions=[
                    AssertionSpec(
                        name="code",
                        selector="code",
                        operator=AssertionOperator.EQUALS,
                        expected=200,
                    )
                ],
                extractors=[
                    ExtractionSpec(
                        name="extract-persona-id",
                        selector="data.records.0.id",
                        source=ExtractionSource.RESPONSE_BODY,
                        target="cache.persona_id",
                    )
                ],
            ),
            CaseDefinition(
                case_id="bind-persona",
                title="绑定评估包",
                request=RequestSpec(
                    method=HttpMethod.POST,
                    url="{{host}}/api/v1/practice/persona/consultation_evaluate_select",
                    headers={"Content-Type": "application/json"},
                    body_type=BodyType.JSON,
                    body={
                        "id": "{{cache.persona_id}}",
                        "evaluationPackageId": "pkg-001",
                    },
                ),
                assertions=[
                    AssertionSpec(
                        name="code",
                        selector="code",
                        operator=AssertionOperator.EQUALS,
                        expected=200,
                    )
                ],
            ),
        ],
    )

    engine = FlowEngine(
        transport=CallableTransport(business_transport),
        plugins=[auth_plugin],
    )
    result = engine.execute_run(run)

    assert result.status == "passed"
    assert seen_headers["list-persona"]["Authorization"] == "real-token-001"
    assert seen_headers["bind-persona"]["Authorization"] == "real-token-001"
