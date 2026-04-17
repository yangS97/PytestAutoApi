"""legacy cache 兼容插件。

这个插件不是为了完整复刻旧框架的所有依赖系统，而是先解决最常见的一条执行级链路：

1. 旧 YAML 里的某个 case 把响应值写入缓存
2. 后面的 case 通过 `$cache{xxx}` 使用这个值

如果没有这个插件，兼容层虽然能把 `$cache{persona_id}` 转成 `{{cache.persona_id}}`，
但运行时 `context.variables["cache"]` 永远不会被真正写入，后续模板渲染自然就会失败。
"""

from typing import Any, Dict

from .._field_path import resolve_field_path
from ..models import ExecutionContext, ResponseSnapshot, TestCaseDefinition
from .base import EnginePlugin


class LegacyCachePlugin(EnginePlugin):
    """最小 legacy cache 插件。"""

    name = "legacy-cache-plugin"

    def after_response(
        self,
        case: TestCaseDefinition,
        response: ResponseSnapshot,
        context: ExecutionContext,
    ) -> None:
        """在响应返回后，把旧缓存规则回写到运行时上下文。"""

        cache_rules = case.request.extras.get("legacy_current_request_set_cache") or []
        if not cache_rules:
            return

        cache_bucket = context.variables.setdefault("cache", {})
        for rule in cache_rules:
            if not isinstance(rule, dict):
                continue
            if str(rule.get("type") or "").lower() != "response":
                continue

            cache_name = str(rule.get("name") or "").strip()
            selector = str(rule.get("jsonpath") or "").strip()
            if not cache_name or not selector:
                continue

            cache_bucket[cache_name] = self._extract_response_value(response.body, selector)

    @staticmethod
    def _extract_response_value(source: Any, selector: str) -> Any:
        """把 legacy JSONPath 简化为当前插件可执行的最小路径。

        当前只覆盖项目里已经出现的主流形态：
        - `$.data.records[0].id`
        - `$.data[0].id`

        这已经足够支撑第一阶段最有代表性的历史用例迁移。
        """

        normalized = selector.replace("$.", "").replace("[", ".").replace("]", "")
        return resolve_field_path(source=source, selector=normalized)

