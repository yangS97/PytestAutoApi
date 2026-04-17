from testflow_engine import (
    BodyType,
    CallableTransport,
    LegacyCachePlugin,
    LegacyYamlCompatLoader,
    ResponseSnapshot,
    SelectorType,
    TestFlowEngine as FlowEngine,
)


def test_legacy_yaml_document_can_convert_to_standard_run_definition():
    """验证 legacy YAML 至少能被桥接到新标准模型。"""

    raw_document = {
        "case_common": {
            "host": "https://example.test",
            "allureEpic": "开发平台接口",
            "allureFeature": "登录模块",
            "allureStory": "登录",
        },
        "login_success": {
            "detail": "用户登录成功",
            "method": "POST",
            "url": "/api/login",
            "headers": {"X-Trace-Id": "trace-001"},
            "requestType": "JSON",
            "data": {"username": "demo", "password": "secret"},
            "assert": [
                {
                    "jsonpath": "$.code",
                    "type": "==",
                    "value": 0,
                    "AssertType": "json",
                }
            ],
            "is_run": True,
        },
    }

    loader = LegacyYamlCompatLoader()
    document = loader.load_from_dict(
        payload=raw_document,
        source_path="data/Login/login.yaml",
    )
    run_definition = loader.to_run_definition(document)
    case = run_definition.cases[0]

    assert document.source_path == "data/Login/login.yaml"
    assert case.source.kind == "legacy_yaml"
    assert case.request.url == "https://example.test/api/login"
    assert case.request.body_type == BodyType.JSON
    assert case.tags == ["开发平台接口", "登录模块", "登录"]
    assert case.assertions[0].selector == "$.code"
    assert case.assertions[0].selector_type == SelectorType.JSONPATH


def test_real_login_yaml_shape_can_be_loaded_from_repo_file():
    """真实仓库里的登录 YAML 应至少能被兼容层读入。

    这个测试的价值不在于“跑真实接口”，而在于防止兼容层只支持我们手写的理想样例，
    却吃不进仓库里已经存在多年的真实数据形态。
    """

    loader = LegacyYamlCompatLoader()
    document = loader.load_from_path("data/Login/login.yaml")
    run_definition = loader.to_run_definition(document, run_name="repo-login-yaml")

    assert run_definition.name == "repo-login-yaml"
    assert len(run_definition.cases) == 3

    first_case = run_definition.cases[0]
    assert first_case.case_id == "login_01"
    assert first_case.title == "正常登录"
    assert first_case.enabled is True
    assert first_case.request.body_type == BodyType.JSON
    assert first_case.request.url == "{{host}}/api/v1/user/password_login"
    assert first_case.assertions[0].name == "code"
    assert first_case.assertions[0].selector == "$.code"
    assert first_case.request.extras["legacy_dependence_case"] is False


def test_persona_yaml_shape_keeps_unmigrated_fields_in_request_extras():
    """更复杂的历史 YAML 字段先保存在 extras，避免迁移时静默丢失。"""

    loader = LegacyYamlCompatLoader()
    document = loader.load_from_path("data/Practice/persona_library_flow.yaml")
    run_definition = loader.to_run_definition(document, run_name="persona-flow")

    first_case = run_definition.cases[0]
    assert first_case.case_id == "persona_lib_01_person_page"
    assert first_case.enabled is True
    assert first_case.request.body_type == BodyType.NONE
    assert run_definition.cases[2].request.url == "{{host}}/api/v1/consultation_evaluate/chapter_list?id={{cache.evaluate_pkg_id}}"
    assert run_definition.cases[4].request.body["evaluationPackageId"] == "{{cache.evaluate_pkg_id}}"
    assert run_definition.cases[4].request.body["id"] == "{{cache.persona_id}}"
    assert first_case.request.extras["legacy_current_request_set_cache"] == [
        {
            "type": "response",
            "jsonpath": "$.data.records[0].id",
            "name": "persona_id",
        }
    ]

    skipped_case = next(case for case in run_definition.cases if case.case_id == "persona_lib_04_select_default")
    assert skipped_case.enabled is False


def test_persona_yaml_can_execute_with_legacy_cache_plugin():
    """真实的人设流 YAML 应能通过最小 cache 兼容插件跑通。

    这个测试比 shape test 更进一步：
    它证明 `$cache{...}` 不只是被转换成占位符，
    而是真的能在执行链路里由前序响应写回上下文，再被后续 case 使用。
    """

    loader = LegacyYamlCompatLoader()
    document = loader.load_from_path("data/Practice/persona_library_flow.yaml")
    run_definition = loader.to_run_definition(document, run_name="persona-flow-exec")
    if hasattr(run_definition, "model_copy"):
        run_definition = run_definition.model_copy(
            update={
                "variables": {
                    "host": "https://example.test",
                }
            },
            deep=True,
        )
    else:
        run_definition = run_definition.copy(
            update={
                "variables": {
                    "host": "https://example.test",
                }
            },
            deep=True,
        )

    response_map = {
        "persona_lib_01_person_page": ResponseSnapshot(
            status_code=200,
            body={"code": 200, "data": {"records": [{"id": "persona-001"}]}},
        ),
        "persona_lib_02_evaluate_page": ResponseSnapshot(
            status_code=200,
            body={"code": 200, "data": [{"id": "pkg-001"}]},
        ),
    }

    engine = FlowEngine(
        transport=CallableTransport(
            lambda request, context, case: response_map.get(
                case.case_id,
                ResponseSnapshot(status_code=200, body={"code": 200, "message": "ok"}),
            )
        ),
        plugins=[LegacyCachePlugin()],
    )
    result = engine.execute_run(run_definition)

    assert result.status == "passed"
    assert result.summary.total == 7
    assert result.summary.passed == 6
    assert result.summary.skipped == 1
