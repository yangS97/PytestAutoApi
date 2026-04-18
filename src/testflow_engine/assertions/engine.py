"""
断言执行骨架。

当前版本只做三件事：
1. 根据 selector/source 从响应或上下文中取值。
2. 执行有限但常用的断言操作。
3. 产出统一的 AssertionResult，交给报告层继续聚合。

后续若引入表达式脚本、数据库断言、快照断言，可以继续在这里扩展。
"""

from typing import Any

from .._field_path import resolve_field_path
from ..models import (
    AssertionOperator,
    AssertionResult,
    AssertionSource,
    AssertionSpec,
    ExecutionContext,
    ExecutionStatus,
    ResponseSnapshot,
    SelectorType,
)

try:
    from jsonpath import jsonpath as jsonpath_extract
except ImportError:  # pragma: no cover - 兼容最小环境
    jsonpath_extract = None


class AssertionEngine:
    """执行标准化断言定义。"""

    def evaluate_all(
        self,
        assertions: list[AssertionSpec],
        response: ResponseSnapshot,
        context: ExecutionContext,
    ) -> list[AssertionResult]:
        """逐条执行断言，并保留每条断言的详细结果。"""

        results = []
        for assertion in assertions:
            results.append(self.evaluate(assertion=assertion, response=response, context=context))
        return results

    def evaluate(
        self,
        assertion: AssertionSpec,
        response: ResponseSnapshot,
        context: ExecutionContext,
    ) -> AssertionResult:
        """执行单条断言。"""

        actual = self._resolve_actual(
            assertion=assertion,
            response=response,
            context=context,
        )
        passed = self._match(
            operator=assertion.operator,
            actual=actual,
            expected=assertion.expected,
        )
        message = assertion.message or self._build_default_message(
            assertion=assertion,
            actual=actual,
        )
        return AssertionResult(
            name=assertion.name,
            status=ExecutionStatus.PASSED if passed else ExecutionStatus.FAILED,
            actual=actual,
            expected=assertion.expected,
            message=message,
        )

    def _resolve_actual(
        self,
        assertion: AssertionSpec,
        response: ResponseSnapshot,
        context: ExecutionContext,
    ) -> Any:
        """根据断言配置解析实际值。"""

        if assertion.source == AssertionSource.STATUS_CODE:
            return response.status_code
        if assertion.source == AssertionSource.RESPONSE_HEADERS:
            return self._extract_value(
                response.headers,
                assertion.selector,
                assertion.selector_type,
            )
        if assertion.source == AssertionSource.CONTEXT:
            return self._extract_value(
                context.variables,
                assertion.selector,
                assertion.selector_type,
            )
        return self._extract_value(
            response.body,
            assertion.selector,
            assertion.selector_type,
            response,
        )

    def _extract_value(
        self,
        source: Any,
        selector: str,
        selector_type: SelectorType,
        response: ResponseSnapshot = None,
    ) -> Any:
        """
        从目标对象里取值。

        这里特意保留 JSONPath 支持，是为了 legacy YAML 能先迁移到新骨架，
        再逐步迁移到平台内部更稳定的 field_path DSL。
        """

        if selector_type == SelectorType.STATUS_CODE and response is not None:
            return response.status_code
        if not selector:
            return source
        if selector_type == SelectorType.JSONPATH:
            return self._extract_jsonpath(source=source, selector=selector)
        return self._extract_field_path(source=source, selector=selector)

    @staticmethod
    def _extract_field_path(source: Any, selector: str) -> Any:
        """按 `data.token` 这样的点路径取值。"""

        return resolve_field_path(source=source, selector=selector)

    def _extract_jsonpath(self, source: Any, selector: str) -> Any:
        """
        优先走 jsonpath 库；若环境里没有该依赖，则退化为简单路径兼容。

        退化逻辑只能覆盖 `$.a.b.c` 这类简单路径，足够支撑骨架阶段的结构测试。
        """

        if jsonpath_extract is not None:
            values = jsonpath_extract(source, selector)
            if values is False:
                return None
            if isinstance(values, list) and len(values) == 1:
                return values[0]
            return values
        normalized = selector.replace("$.", "").replace("[", ".").replace("]", "")
        return self._extract_field_path(source=source, selector=normalized)

    @staticmethod
    def _match(operator: AssertionOperator, actual: Any, expected: Any) -> bool:
        """根据操作符比较 actual 和 expected。"""

        if operator == AssertionOperator.EQUALS:
            return actual == expected
        if operator == AssertionOperator.NOT_EQUALS:
            return actual != expected
        if operator == AssertionOperator.CONTAINS:
            if actual is None:
                return False
            return expected in actual
        if operator == AssertionOperator.EXISTS:
            return actual is not None
        if operator == AssertionOperator.GREATER_THAN:
            return actual > expected
        if operator == AssertionOperator.GREATER_OR_EQUAL:
            return actual >= expected
        if operator == AssertionOperator.LESS_THAN:
            return actual < expected
        if operator == AssertionOperator.LESS_OR_EQUAL:
            return actual <= expected
        raise ValueError(f"不支持的断言操作: {operator}")

    @staticmethod
    def _build_default_message(assertion: AssertionSpec, actual: Any) -> str:
        """生成默认断言消息，方便报告层直接展示。"""

        return f"断言[{assertion.name}] 实际值={actual!r} 期望值={assertion.expected!r}"
