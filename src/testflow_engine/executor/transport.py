"""
传输层抽象。

执行器不应该直接绑定 requests/httpx，否则未来切到：
- 真实 HTTP 调用
- Mock Transport
- 录制回放
- 异步 worker 内的特殊网络策略
都会牵连主执行链路。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from time import perf_counter
from typing import TYPE_CHECKING, Any, Callable, Optional

from ..models import BodyType, ExecutionContext, RequestSpec, ResponseSnapshot, TestCaseDefinition

if TYPE_CHECKING:  # pragma: no cover - 仅用于类型提示
    import httpx


class TransportNotConfiguredError(RuntimeError):
    """执行器没有配置 Transport 时抛出的错误。"""


class TransportAdapter(ABC):
    """传输层接口。"""

    @abstractmethod
    def send(
        self,
        request: RequestSpec,
        context: ExecutionContext,
        case: TestCaseDefinition,
    ) -> ResponseSnapshot:
        """发送请求并返回标准响应。"""


class CallableTransport(TransportAdapter):
    """
    便于测试和早期接入的轻量 transport。

    调用方只要提供一个函数，就能快速把平台已有 HTTP 能力挂进新引擎。
    """

    def __init__(self, handler: Callable[[RequestSpec, ExecutionContext, TestCaseDefinition], Any]):
        self._handler = handler

    def send(
        self,
        request: RequestSpec,
        context: ExecutionContext,
        case: TestCaseDefinition,
    ) -> ResponseSnapshot:
        result = self._handler(request, context, case)
        if isinstance(result, ResponseSnapshot):
            return result
        if isinstance(result, dict):
            return ResponseSnapshot(**result)
        raise TypeError("transport handler 必须返回 ResponseSnapshot 或 dict")


class HttpxTransport(TransportAdapter):
    """
    基于 httpx 的真实 transport。

    为什么还要保留这一层抽象，而不是让执行器直接调用 httpx：
    1. 测试时可以替换成 CallableTransport / MockTransport，不需要真的出网。
    2. 以后若接入录制回放、重试、代理、异步 transport，执行器不用跟着改。
    """

    def __init__(self, client: Optional["httpx.Client"] = None, *, follow_redirects: bool = True) -> None:
        httpx_module = _load_httpx()
        self._client = client or httpx_module.Client(follow_redirects=follow_redirects)
        self._owns_client = client is None

    def close(self) -> None:
        """关闭内部创建的 client，方便长生命周期服务显式释放连接池。"""

        if self._owns_client:
            self._client.close()

    def send(
        self,
        request: RequestSpec,
        context: ExecutionContext,
        case: TestCaseDefinition,
    ) -> ResponseSnapshot:
        """
        发送已渲染好的请求。

        注意：变量渲染不在这里做。transport 只处理“把标准请求模型翻译成 httpx 调用”。
        """

        started_at = perf_counter()
        response = self._client.request(
            method=request.method.value,
            url=request.url,
            headers=request.headers or None,
            params=self._build_query_params(request),
            timeout=request.timeout_seconds,
            **self._build_body_kwargs(request),
        )
        elapsed_ms = (perf_counter() - started_at) * 1000
        return ResponseSnapshot(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=self._decode_response_body(response),
            elapsed_ms=elapsed_ms,
            request_id=response.headers.get("x-request-id") or response.headers.get("x-trace-id"),
        )

    @staticmethod
    def _build_query_params(request: RequestSpec) -> Any:
        """组装 query 参数，并兼容 legacy `requestType=PARAMS` 的迁移结果。"""

        httpx_module = _load_httpx()
        if request.body_type != BodyType.QUERY or request.body is None:
            return request.query or None
        if not request.query:
            return request.body
        return list(httpx_module.QueryParams(request.query).multi_items()) + list(
            httpx_module.QueryParams(request.body).multi_items()
        )

    @classmethod
    def _build_body_kwargs(cls, request: RequestSpec) -> dict[str, Any]:
        """根据 body_type 把标准模型映射为 httpx 参数。"""

        if request.body is None or request.body_type in {BodyType.NONE, BodyType.QUERY}:
            return {}
        if request.body_type == BodyType.JSON:
            return {"json": request.body}
        if request.body_type == BodyType.FORM:
            return {"data": request.body}
        if request.body_type == BodyType.FILE:
            if not isinstance(request.body, (Mapping, list, tuple)):
                raise TypeError("FILE 请求的 body 必须是 httpx 可接受的 files 结构")
            return {"files": request.body}
        if request.body_type == BodyType.RAW:
            return {"content": cls._coerce_raw_body(request.body)}
        return {"content": request.body}

    @staticmethod
    def _coerce_raw_body(body: Any) -> Any:
        """RAW 请求允许传入文本或二进制；其他类型退化为字符串。"""

        if isinstance(body, (str, bytes, bytearray)):
            return body
        return str(body)

    @staticmethod
    def _decode_response_body(response: httpx.Response) -> Any:
        """优先解析 JSON，其次返回文本；纯二进制内容则保留 bytes。"""

        if not response.content:
            return None

        content_type = response.headers.get("content-type", "").lower()
        if "json" in content_type:
            try:
                return response.json()
            except ValueError:
                return response.text
        if content_type.startswith("text/") or "xml" in content_type or "html" in content_type:
            return response.text
        return response.content


def _load_httpx():
    """按需导入 httpx，避免环境缺依赖时连非 transport 场景也无法导入包。"""

    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - 依赖缺失属于环境问题
        raise RuntimeError(
            "HttpxTransport 依赖 httpx，请先安装项目依赖后再使用真实 HTTP transport"
        ) from exc
    return httpx
