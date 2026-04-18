"""
请求变量渲染。

这层故意放在执行器侧，而不是 transport 里，原因有两个：
1. transport 只关心“怎么发送已经确定好的请求”，保持网络适配职责单一。
2. 变量来自运行时 context，属于执行编排问题，应该在进入 transport 之前解决。

当前阶段只支持最轻量的 `{{var}}` 模板，不扩成完整 DSL。
"""

from __future__ import annotations

import re
from typing import Any

from .._field_path import has_field_path, resolve_field_path
from ..models import ExecutionContext, RequestSpec

_TEMPLATE_PATTERN = re.compile(r"{{\s*([^{}]+?)\s*}}")


class MissingTemplateVariableError(KeyError):
    """模板中引用了未定义变量时抛出。"""


class RequestTemplateRenderer:
    """把请求里的轻量模板替换成运行时变量。"""

    def render(self, request: RequestSpec, context: ExecutionContext) -> RequestSpec:
        """
        渲染请求并返回新对象。

        这里不直接修改原始 RequestSpec，是为了保留“用例定义”和“本次执行实际请求”
        这两个边界，后续做调试对比会更清晰。
        """

        update = {
            "url": self._render_value(request.url, context),
            "headers": self._render_value(request.headers, context),
            "query": self._render_value(request.query, context),
            "body": self._render_value(request.body, context),
        }
        if hasattr(request, "model_copy"):
            return request.model_copy(update=update, deep=True)
        return request.copy(update=update, deep=True)

    def _render_value(self, value: Any, context: ExecutionContext) -> Any:
        """递归渲染字符串、字典、列表等结构。"""

        if isinstance(value, dict):
            return {
                self._render_string(key, context) if isinstance(key, str) else key:
                self._render_value(item, context)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [self._render_value(item, context) for item in value]
        if isinstance(value, tuple):
            return tuple(self._render_value(item, context) for item in value)
        if isinstance(value, str):
            return self._render_string(value, context)
        return value

    def _render_string(self, template: str, context: ExecutionContext) -> Any:
        """
        渲染单个字符串模板。

        若整个字符串就是一个占位符，例如 `{{user.id}}`，则保留变量原始类型；
        这样 body/query 里的数字、布尔值不会被强制转成字符串。
        """

        match = _TEMPLATE_PATTERN.fullmatch(template)
        if match:
            return self._resolve_variable(match.group(1), context)

        def replacer(match_obj: re.Match[str]) -> str:
            value = self._resolve_variable(match_obj.group(1), context)
            return "" if value is None else str(value)

        return _TEMPLATE_PATTERN.sub(replacer, template)

    @staticmethod
    def _resolve_variable(selector: str, context: ExecutionContext) -> Any:
        """从上下文变量中读取模板值，未定义时直接失败，避免把脏请求发出去。"""

        if not has_field_path(context.variables, selector):
            raise MissingTemplateVariableError(f"模板变量未定义: {selector}")
        return resolve_field_path(context.variables, selector)
