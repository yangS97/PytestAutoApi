from testflow_engine import (
    AssertionOperator,
    AssertionSource,
    AssertionSpec,
    CallableTransport,
    EnginePlugin,
    HttpMethod,
    ReportCollector,
    RequestSpec,
    ResponseSnapshot,
    TestCaseDefinition as CaseDefinition,
    TestFlowEngine as FlowEngine,
    TestRunDefinition as RunDefinition,
)


class TracePlugin(EnginePlugin):
    """测试用插件，用来验证生命周期 hook 已经打通。"""

    name = "trace-plugin"

    def before_run(self, run, context):
        context.set_variable("before_run", run.name)

    def before_case(self, case, context):
        context.set_variable("active_case", case.case_id)


def test_public_engine_can_execute_basic_run():
    """最小闭环测试：run -> case -> transport -> assertion -> report。"""

    def fake_transport(request, context, case):
        assert request.method == HttpMethod.POST
        assert context.get_variable("before_run") == "engine-smoke"
        assert context.get_variable("active_case") == case.case_id
        return ResponseSnapshot(
            status_code=200,
            headers={"content-type": "application/json"},
            body={"code": 0, "data": {"token": "abc123"}},
            elapsed_ms=12.5,
        )

    case = CaseDefinition(
        case_id="case-login-001",
        title="登录成功",
        request=RequestSpec(
            method=HttpMethod.POST,
            url="https://example.test/api/login",
            body={"username": "demo", "password": "secret"},
        ),
        assertions=[
            AssertionSpec(
                name="status-code",
                source=AssertionSource.STATUS_CODE,
                operator=AssertionOperator.EQUALS,
                expected=200,
            ),
            AssertionSpec(
                name="business-code",
                selector="code",
                operator=AssertionOperator.EQUALS,
                expected=0,
            ),
            AssertionSpec(
                name="token-exists",
                selector="data.token",
                operator=AssertionOperator.EXISTS,
            ),
        ],
    )
    engine = FlowEngine(
        transport=CallableTransport(fake_transport),
        plugins=[TracePlugin()],
        report_collector=ReportCollector(),
    )

    result = engine.execute_run(RunDefinition(name="engine-smoke", cases=[case]))

    assert result.status == "passed"
    assert result.summary.total == 1
    assert result.summary.passed == 1
    assert result.cases[0].steps[0].response.status_code == 200
    assert len(result.cases[0].steps[0].assertions) == 3


def test_engine_renders_request_variables_before_transport_send():
    """执行器应先渲染模板，再把最终请求交给 transport。"""

    captured = {}

    def fake_transport(request, context, case):
        captured["request"] = request
        assert case.case_id == "case-render-001"
        assert context.get_variable("auth.token") is None
        return ResponseSnapshot(status_code=200, body={"code": 0})

    case = CaseDefinition(
        case_id="case-render-001",
        title="渲染请求变量",
        request=RequestSpec(
            method=HttpMethod.POST,
            url="{{base_url}}/api/users/{{user.id}}",
            headers={
                "Authorization": "{{auth.token}}",
                "X-Trace-Id": "trace-{{trace_id}}",
            },
            query={
                "user_id": "{{user.id}}",
                "keyword": "{{keyword}}",
            },
            body={
                "user_id": "{{user.id}}",
                "enabled": "{{enabled}}",
                "profile": "{{profile}}",
                "note": "request-{{trace_id}}",
            },
        ),
        assertions=[
            AssertionSpec(
                name="status-code",
                source=AssertionSource.STATUS_CODE,
                operator=AssertionOperator.EQUALS,
                expected=200,
            )
        ],
    )
    run = RunDefinition(
        name="engine-render",
        cases=[case],
        variables={
            "base_url": "https://example.test",
            "user": {"id": 1001},
            "auth": {"token": "Bearer demo-token"},
            "trace_id": "trace-001",
            "keyword": "demo",
            "enabled": True,
            "profile": {"role": "tester"},
        },
    )
    engine = FlowEngine(transport=CallableTransport(fake_transport))

    result = engine.execute_run(run)
    rendered_request = captured["request"]

    assert result.status == "passed"
    assert rendered_request.url == "https://example.test/api/users/1001"
    assert rendered_request.headers == {
        "Authorization": "Bearer demo-token",
        "X-Trace-Id": "trace-trace-001",
    }
    assert rendered_request.query == {"user_id": 1001, "keyword": "demo"}
    assert rendered_request.body == {
        "user_id": 1001,
        "enabled": True,
        "profile": {"role": "tester"},
        "note": "request-trace-001",
    }
    # 原始用例定义仍然保留模板，方便后续调试“定义值”和“实际发送值”的差异。
    assert case.request.url == "{{base_url}}/api/users/{{user.id}}"
    assert case.request.body["profile"] == "{{profile}}"
