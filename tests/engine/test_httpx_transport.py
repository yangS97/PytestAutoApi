import json

import pytest

from testflow_engine import (
    BodyType,
    ExecutionContext,
    HttpMethod,
    HttpxTransport,
    RequestSpec,
)
from testflow_engine import (
    TestCaseDefinition as CaseDefinition,
)

httpx = pytest.importorskip("httpx")


def _build_case(request: RequestSpec) -> CaseDefinition:
    """构造最小 case，方便直接测试 transport。"""

    return CaseDefinition(case_id="transport-case", title="transport", request=request)


def test_httpx_transport_can_send_json_request_via_mock_transport():
    """真实 transport 应能把标准请求模型正确翻译成 httpx 请求。"""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == "https://example.test/api/login?channel=web"
        assert request.headers["authorization"] == "Bearer demo-token"
        assert json.loads(request.content.decode("utf-8")) == {
            "username": "demo",
            "password": "secret",
        }
        return httpx.Response(
            201,
            json={"code": 0, "message": "ok"},
            headers={"x-request-id": "req-001"},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    transport = HttpxTransport(client=client)
    request = RequestSpec(
        method=HttpMethod.POST,
        url="https://example.test/api/login",
        headers={"Authorization": "Bearer demo-token"},
        query={"channel": "web"},
        body_type=BodyType.JSON,
        body={"username": "demo", "password": "secret"},
        timeout_seconds=5,
    )

    try:
        snapshot = transport.send(
            request=request,
            context=ExecutionContext(run_id="run-httpx"),
            case=_build_case(request),
        )
    finally:
        client.close()

    assert snapshot.status_code == 201
    assert snapshot.headers["x-request-id"] == "req-001"
    assert snapshot.headers["content-type"] == "application/json"
    # content-length 由 httpx 根据最终响应体自动计算，这里只校验它被正确带出，
    # 不把测试绑死在某个具体数字上，避免因为序列化细节变化导致伪失败。
    assert snapshot.headers["content-length"].isdigit()
    assert snapshot.body == {"code": 0, "message": "ok"}
    assert snapshot.request_id == "req-001"
    assert snapshot.elapsed_ms >= 0


def test_httpx_transport_merges_query_body_for_query_request_type():
    """legacy PARAMS 迁移到 BodyType.QUERY 后，transport 仍应正确拼 query。"""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert str(request.url) == "https://example.test/api/search?fixed=1&keyword=books&page=2"
        assert request.content == b""
        return httpx.Response(200, json={"items": []})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    transport = HttpxTransport(client=client)
    request = RequestSpec(
        method=HttpMethod.GET,
        url="https://example.test/api/search",
        query={"fixed": "1"},
        body_type=BodyType.QUERY,
        body={"keyword": "books", "page": 2},
    )

    try:
        snapshot = transport.send(
            request=request,
            context=ExecutionContext(run_id="run-query"),
            case=_build_case(request),
        )
    finally:
        client.close()

    assert snapshot.status_code == 200
    assert snapshot.body == {"items": []}
