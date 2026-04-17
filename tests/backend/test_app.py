"""平台后端骨架的最小测试。"""

import importlib
import sys

from fake_fastapi import install_fake_fastapi


def _reload_backend_modules(monkeypatch):
    """在注入 fake fastapi 后重新加载后端模块。"""

    install_fake_fastapi(monkeypatch)

    for module_name in list(sys.modules):
        if module_name == "pyta_platform_backend" or module_name.startswith("pyta_platform_backend."):
            sys.modules.pop(module_name, None)

    app_module = importlib.import_module("pyta_platform_backend.app")
    config_module = importlib.import_module("pyta_platform_backend.config")
    run_schema_module = importlib.import_module("pyta_platform_backend.schemas.run")
    return app_module, config_module, run_schema_module


def _find_route(app, path: str, method: str):
    """按路径和方法查找注册后的路由。"""

    for route in app.routes:
        if route.path == path and method in route.methods:
            return route
    raise AssertionError(f"未找到路由: {method} {path}")


def test_create_app_registers_routes_and_health_endpoint(monkeypatch):
    """应用创建后应注册核心路由，并能返回最小健康信息。"""

    app_module, config_module, _ = _reload_backend_modules(monkeypatch)
    settings = config_module.BackendSettings(
        app_name="Platform Backend Test",
        app_env="test",
        api_prefix="/api/test",
    )

    app = app_module.create_app(settings=settings)

    assert app.title == "Platform Backend Test"
    assert app.state.settings.app_env == "test"
    assert app.state.scheduler.poll_interval_seconds == settings.scheduler_poll_interval_seconds
    assert app.state.dashboard_service is not None

    dashboard_route = _find_route(app, "/api/test/dashboard/overview", "GET")
    demo_suites_route = _find_route(app, "/api/test/demo-suites", "GET")
    live_route = _find_route(app, "/api/test/health/live", "GET")
    runs_route = _find_route(app, "/api/test/runs", "POST")
    worker_route = _find_route(app, "/api/test/worker/run-next", "POST")

    overview_payload = dashboard_route.endpoint()
    demo_suites_payload = demo_suites_route.endpoint()
    health_payload = live_route.endpoint()
    assert health_payload.status == "ok"
    assert health_payload.environment == "test"
    assert overview_payload.metrics
    assert demo_suites_payload.items
    assert runs_route.status_code == 202
    assert worker_route.status_code == 200


def test_create_run_endpoint_only_persists_and_dispatches(monkeypatch):
    """创建 run 的路由只负责写入主真源并投递 worker。"""

    app_module, config_module, run_schema_module = _reload_backend_modules(monkeypatch)
    settings = config_module.BackendSettings(
        app_env="test",
        run_dispatch_channel="test-memory-worker",
    )
    app = app_module.create_app(settings=settings)

    create_run_route = _find_route(app, "/api/v1/runs", "POST")
    payload = run_schema_module.CreateRunRequest(
        suite_id="smoke-suite",
        trigger_source="manual",
        requested_by="tester",
        payload={"retry": 0},
    )

    response = create_run_route.endpoint(payload)

    stored_record = app.state.run_service.repository.get_by_id(response.run_id)
    dispatched_task = app.state.run_service.dispatcher.dispatched_tasks[0]

    assert stored_record is not None
    assert stored_record.status.value == "queued"
    assert stored_record.run_id == response.run_id
    assert dispatched_task.run_id == response.run_id
    assert response.dispatch_channel == "test-memory-worker"
    assert dispatched_task.dispatched_at == stored_record.created_at


def test_runs_routes_support_list_detail_and_status_update(monkeypatch):
    """run 链路应支持结果页第一阶段最需要的三个动作。"""

    app_module, config_module, run_schema_module = _reload_backend_modules(monkeypatch)
    settings = config_module.BackendSettings(app_env="test")
    app = app_module.create_app(settings=settings)

    create_run_route = _find_route(app, "/api/v1/runs", "POST")
    list_runs_route = _find_route(app, "/api/v1/runs", "GET")
    detail_route = _find_route(app, "/api/v1/runs/{run_id}", "GET")
    patch_route = _find_route(app, "/api/v1/runs/{run_id}/status", "PATCH")

    created = create_run_route.endpoint(
        run_schema_module.CreateRunRequest(
            suite_id="nightly-suite",
            trigger_source="scheduler",
            requested_by="system",
            payload={"tenant": "demo"},
        )
    )

    list_payload = list_runs_route.endpoint(limit=20, offset=0)
    assert list_payload.total == 1
    assert list_payload.items[0].run_id == created.run_id
    assert list_payload.items[0].status.value == "queued"

    detail_payload = detail_route.endpoint(created.run_id)
    assert detail_payload.run_id == created.run_id
    assert detail_payload.payload == {"tenant": "demo"}

    patched = patch_route.endpoint(
        created.run_id,
        run_schema_module.UpdateRunStatusRequest(
            status=run_schema_module.RunStatus.RUNNING,
            status_message="worker started",
        ),
    )
    assert patched.status.value == "running"
    assert patched.status_message == "worker started"


def test_memory_worker_runner_can_consume_dispatched_task(monkeypatch):
    """最小 worker 应能消费 dispatcher 中的任务并回写成功状态。"""

    app_module, config_module, run_schema_module = _reload_backend_modules(monkeypatch)
    settings = config_module.BackendSettings(app_env="test")
    app = app_module.create_app(settings=settings)

    created = app.state.run_service.create_run(
        run_schema_module.CreateRunRequest(
            suite_id="smoke-worker-suite",
            trigger_source="manual",
            requested_by="tester",
            payload={"tenant": "demo"},
        )
    )
    detail = app.state.worker_runner.run_next()

    assert detail is not None
    assert detail.run_id == created.run_id
    assert detail.status.value == "succeeded"
    assert "memory worker finished suite smoke-worker-suite" in (detail.status_message or "")
    assert app.state.run_service.dispatcher.dispatched_tasks == []


def test_memory_worker_runner_marks_run_failed_when_handler_raises(monkeypatch):
    """worker 执行异常时应把 run 回写为 failed，而不是静默吞掉。"""

    app_module, config_module, run_schema_module = _reload_backend_modules(monkeypatch)
    runner_module = importlib.import_module("pyta_platform_backend.workers.runner")
    settings = config_module.BackendSettings(app_env="test")
    app = app_module.create_app(settings=settings)

    app.state.run_service.create_run(
        run_schema_module.CreateRunRequest(
            suite_id="boom-suite",
            trigger_source="manual",
            requested_by="tester",
            payload={},
        )
    )
    broken_runner = runner_module.MemoryWorkerRunner(
        dispatcher=app.state.run_service.dispatcher,
        run_service=app.state.run_service,
        handler=lambda task: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    detail = broken_runner.run_next()

    assert detail is not None
    assert detail.status.value == "failed"
    assert detail.status_message == "boom"


def test_memory_worker_runner_can_execute_legacy_yaml_through_new_engine(monkeypatch):
    """worker 应能消费 legacy YAML 任务，并通过新引擎给出成功摘要。"""

    app_module, config_module, run_schema_module = _reload_backend_modules(monkeypatch)
    settings = config_module.BackendSettings(app_env="test")
    app = app_module.create_app(settings=settings)

    app.state.run_service.create_run(
        run_schema_module.CreateRunRequest(
            suite_id="legacy-login-suite",
            trigger_source="manual",
            requested_by="tester",
            payload={
                "execution_mode": "legacy_yaml",
                "legacy_yaml_path": "data/Login/login.yaml",
                "variables": {
                    "host": "https://example.test",
                },
                "mock_case_responses": {
                    "login_01": {
                        "status_code": 200,
                        "body": {"code": 200},
                        "headers": {"content-type": "application/json"},
                    },
                    "login_02": {
                        "status_code": 200,
                        "body": {"code": 500},
                        "headers": {"content-type": "application/json"},
                    },
                    "login_03": {
                        "status_code": 200,
                        "body": {"code": 500},
                        "headers": {"content-type": "application/json"},
                    },
                },
            },
        )
    )

    detail = app.state.worker_runner.run_next()

    assert detail is not None
    assert detail.status.value == "succeeded"
    assert detail.status_message is not None
    assert "legacy yaml executed from data/Login/login.yaml" in detail.status_message
    assert "total=3" in detail.status_message
    assert "passed=3" in detail.status_message


def test_demo_suites_route_can_create_standard_run(monkeypatch):
    """样例套件接口应能列出迁移样例，并创建标准化 run。"""

    app_module, config_module, _ = _reload_backend_modules(monkeypatch)
    settings = config_module.BackendSettings(app_env="test")
    app = app_module.create_app(settings=settings)

    list_demo_route = _find_route(app, "/api/v1/demo-suites", "GET")
    create_demo_route = _find_route(app, "/api/v1/demo-suites/{suite_id}/runs", "POST")
    run_next_route = _find_route(app, "/api/v1/worker/run-next", "POST")
    demo_schema_module = importlib.import_module("pyta_platform_backend.schemas.demo_suite")

    suites_payload = list_demo_route.endpoint()
    suite_ids = [item.suite_id for item in suites_payload.items]
    assert "demo-login-auth" in suite_ids
    assert "demo-persona-library" in suite_ids

    response = create_demo_route.endpoint(
        "demo-login-auth",
        demo_schema_module.CreateDemoSuiteRunRequest(
            mode="mock",
            requested_by="tester",
        ),
    )

    assert response.suite_id == "demo-login-auth"
    assert response.mode == "mock"
    stored_record = app.state.run_service.repository.get_by_id(response.run_id)
    assert stored_record is not None
    assert stored_record.payload["execution_mode"] == "standard_run"
    worker_result = run_next_route.endpoint()
    assert worker_result.consumed is True
    assert worker_result.detail is not None
    assert worker_result.detail.run_id == response.run_id
    assert worker_result.detail.status.value == "succeeded"
