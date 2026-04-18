"""
legacy YAML 兼容层骨架。

目标不是把旧框架逻辑原样照搬，而是先提供一座桥：
legacy YAML -> 新引擎标准模型

这样迁移可以分两步走：
1. 先让旧数据能在新引擎里跑起来。
2. 再逐步把 YAML 字段下沉到平台主真源和新的 DSL。

这一层有一个很现实的设计原则：
只要老 YAML 的某个字段“暂时还没法在新引擎里真正执行”，
也不要立刻丢弃，而是优先保存在 metadata/extras 中。

原因是迁移阶段最怕两种情况：
1. 旧字段直接消失，后面根本不知道还有什么能力没迁过来。
2. 还没迁完就强行上线，导致历史用例语义悄悄变化。
"""

import re
from collections.abc import Iterable
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field

from ..models import (
    AssertionOperator,
    AssertionSource,
    AssertionSpec,
    BodyType,
    CaseSource,
    HttpMethod,
    RequestSpec,
    SelectorType,
    TestCaseDefinition,
    TestRunDefinition,
)


class LegacyYamlDocument(BaseModel):
    """解析后的 legacy YAML 文档。"""

    source_path: Optional[str] = None
    case_common: dict[str, Any] = Field(default_factory=dict)
    raw_cases: dict[str, dict[str, Any]] = Field(default_factory=dict)


class LegacyYamlCompatLoader:
    """把 legacy YAML 文档转换为新引擎可执行模型。"""

    # 旧 YAML 里常见的函数模板是 `${{host()}}` 这种形式。
    # 新引擎第一阶段不直接执行这些函数，而是统一转换为普通变量占位，
    # 后续由 ExecutionContext.variables 提供真实值。
    LEGACY_FUNCTION_TEMPLATE_PATTERN = re.compile(r"\$\{\{\s*([a-zA-Z_][\w]*)\(\)\s*\}\}")
    LEGACY_CACHE_TEMPLATE_PATTERN = re.compile(r"\$cache\{([^{}]+)\}")

    LEGACY_REQUEST_TYPE_MAP = {
        "JSON": BodyType.JSON,
        "DATA": BodyType.FORM,
        "PARAMS": BodyType.QUERY,
        "FILE": BodyType.FILE,
        "NONE": BodyType.NONE,
        "EXPORT": BodyType.RAW,
    }

    LEGACY_ASSERT_OPERATOR_MAP = {
        "==": AssertionOperator.EQUALS,
        "not_eq": AssertionOperator.NOT_EQUALS,
        "contains": AssertionOperator.CONTAINS,
        "lt": AssertionOperator.LESS_THAN,
        "le": AssertionOperator.LESS_OR_EQUAL,
        "gt": AssertionOperator.GREATER_THAN,
        "ge": AssertionOperator.GREATER_OR_EQUAL,
    }

    def load_from_path(self, path: str) -> LegacyYamlDocument:
        """从 YAML 文件加载 legacy 文档。"""

        with open(path, encoding="utf-8") as file:
            payload = yaml.safe_load(file) or {}
        return self.load_from_dict(payload=payload, source_path=path)

    def load_from_dict(
        self,
        payload: dict[str, Any],
        source_path: str = None,
    ) -> LegacyYamlDocument:
        """从字典直接构造 legacy 文档，方便测试和后续平台接入。"""

        case_common = payload.get("case_common") or {}
        raw_cases = {
            key: value
            for key, value in payload.items()
            if key != "case_common" and isinstance(value, dict)
        }
        return LegacyYamlDocument(
            source_path=source_path,
            case_common=case_common,
            raw_cases=raw_cases,
        )

    def to_run_definition(
        self,
        document: LegacyYamlDocument,
        run_name: str = "legacy-yaml-run",
    ) -> TestRunDefinition:
        """把 legacy 文档转换成一组标准化 case。"""

        cases = []
        for case_id, raw_case in document.raw_cases.items():
            cases.append(
                self._convert_case(
                    case_id=case_id,
                    raw_case=raw_case,
                    case_common=document.case_common,
                    source_path=document.source_path,
                )
            )
        return TestRunDefinition(
            name=run_name,
            cases=cases,
            metadata={
                "legacy_yaml_path": document.source_path,
                "compat_mode": "legacy_yaml",
            },
        )

    def _convert_case(
        self,
        case_id: str,
        raw_case: dict[str, Any],
        case_common: dict[str, Any],
        source_path: str = None,
    ) -> TestCaseDefinition:
        """转换单个 legacy case。"""

        host = raw_case.get("host") or case_common.get("host") or ""
        url = raw_case.get("url") or ""
        request = RequestSpec(
            method=self._map_method(raw_case.get("method")),
            url=self._normalize_legacy_templates(self._join_url(host=host, url=url)),
            headers=self._normalize_legacy_templates(raw_case.get("headers") or {}),
            body_type=self._map_request_type(raw_case.get("requestType")),
            body=self._normalize_legacy_templates(raw_case.get("data")),
            extras={
                "legacy_request_type": raw_case.get("requestType"),
                "legacy_sleep": raw_case.get("sleep"),
                # 这些字段当前还没有被真正执行，但先明确保留，避免迁移时信息丢失。
                "legacy_dependence_case": raw_case.get("dependence_case"),
                "legacy_dependence_case_data": raw_case.get("dependence_case_data"),
                "legacy_current_request_set_cache": raw_case.get("current_request_set_cache"),
                "legacy_teardown": raw_case.get("teardown"),
                "legacy_teardown_sql": raw_case.get("teardown_sql"),
                "legacy_sql": raw_case.get("sql"),
            },
        )
        return TestCaseDefinition(
            case_id=case_id,
            title=raw_case.get("detail") or case_id,
            description="由 legacy YAML 自动转换而来，后续应逐步迁移到平台真源。",
            request=request,
            assertions=self._convert_assertions(raw_case.get("assert") or []),
            enabled=self._resolve_enabled_flag(raw_case.get("is_run")),
            tags=self._build_tags(case_common=case_common),
            metadata={
                "legacy_case_common": case_common,
                "legacy_raw_case": raw_case,
            },
            source=CaseSource(
                kind="legacy_yaml",
                path=source_path,
                raw=raw_case,
            ),
        )

    def _convert_assertions(self, legacy_assertions: Any) -> list[AssertionSpec]:
        """把 legacy assert 转换成标准断言。

        旧仓库里真实出现过两种写法：
        1. 列表写法：[{jsonpath: ..., type: ..., value: ...}]
        2. 字典写法：{code: {jsonpath: ..., type: ..., value: ...}}

        兼容层这里把两种格式统一摊平成迭代序列，避免后续断言层感知历史差异。
        """

        assertions = []
        for index, (legacy_name, item) in enumerate(
            self._iter_legacy_assert_items(legacy_assertions),
            start=1,
        ):
            selector = item.get("jsonpath") or ""
            assertions.append(
                AssertionSpec(
                    name=item.get("name") or legacy_name or f"legacy-assert-{index}",
                    selector=selector,
                    selector_type=SelectorType.JSONPATH if selector else SelectorType.FIELD_PATH,
                    source=AssertionSource.RESPONSE_BODY,
                    operator=self._map_assert_operator(item.get("type")),
                    expected=item.get("value"),
                    message="兼容层从 legacy YAML 迁移的断言",
                    extras={"legacy_assert_type": item.get("AssertType")},
                )
            )
        return assertions

    @staticmethod
    def _iter_legacy_assert_items(
        legacy_assertions: Any,
    ) -> Iterable[tuple[Optional[str], dict[str, Any]]]:
        """把旧断言结构统一展开成 `(name, payload)` 序列。"""

        if isinstance(legacy_assertions, list):
            for item in legacy_assertions:
                if isinstance(item, dict):
                    yield None, item
            return

        if isinstance(legacy_assertions, dict):
            for key, value in legacy_assertions.items():
                if isinstance(value, dict):
                    yield str(key), value

    @staticmethod
    def _resolve_enabled_flag(raw_value: Any) -> bool:
        """解析旧 YAML 里的 is_run 字段。

        真实历史数据里经常出现三种情况：
        1. `is_run: True`
        2. `is_run: False`
        3. `is_run:` 留空

        对测试同学来说，留空通常意味着“默认执行”，而不是“默认关闭”。
        所以这里把 `None / 空字符串` 都当作 True。
        """

        if raw_value is None:
            return True
        if isinstance(raw_value, str) and raw_value.strip() == "":
            return True
        if isinstance(raw_value, bool):
            return raw_value
        return bool(raw_value)

    @classmethod
    def _build_tags(cls, case_common: dict[str, Any]) -> list[str]:
        """从 legacy 的 allure 标签衍生出基础 tags。"""

        tags = []
        for key in ("allureEpic", "allureFeature", "allureStory"):
            value = case_common.get(key)
            if value:
                tags.append(str(value))
        return tags

    @classmethod
    def _map_method(cls, raw_method: Any) -> HttpMethod:
        """把 legacy method 转为枚举。"""

        normalized = str(raw_method or "GET").upper()
        return HttpMethod(normalized)

    def _map_request_type(self, raw_type: Any) -> BodyType:
        """把 legacy requestType 转为新引擎 body_type。"""

        normalized = str(raw_type or "JSON").upper()
        return self.LEGACY_REQUEST_TYPE_MAP.get(normalized, BodyType.JSON)

    def _map_assert_operator(self, raw_operator: Any) -> AssertionOperator:
        """把 legacy 断言操作映射为新引擎内置操作。"""

        normalized = str(raw_operator or "==")
        return self.LEGACY_ASSERT_OPERATOR_MAP.get(normalized, AssertionOperator.EQUALS)

    @staticmethod
    def _join_url(host: str, url: str) -> str:
        """拼接 host + url，同时兼容 host 为空的情况。"""

        if not host:
            return url
        if not url:
            return host
        return host.rstrip("/") + "/" + url.lstrip("/")

    def _normalize_legacy_templates(self, value: Any) -> Any:
        """把旧模板语法转成新引擎当前可理解的轻量占位符。

        这一步非常关键，因为旧框架里最常见的动态值写法并不是 `{{host}}`，
        而是：

        - `${{host()}}`
        - `$cache{token}`

        如果不先做一层语法规整，新引擎就算有模板渲染器，也吃不进这些真实历史数据。
        """

        if isinstance(value, dict):
            return {
                self._normalize_legacy_templates(key) if isinstance(key, str) else key:
                self._normalize_legacy_templates(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [self._normalize_legacy_templates(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self._normalize_legacy_templates(item) for item in value)
        if not isinstance(value, str):
            return value

        normalized = self.LEGACY_FUNCTION_TEMPLATE_PATTERN.sub(self._replace_legacy_function, value)
        normalized = self.LEGACY_CACHE_TEMPLATE_PATTERN.sub(self._replace_legacy_cache, normalized)
        return normalized

    @staticmethod
    def _replace_legacy_function(match: re.Match) -> str:
        """把 `${{host()}}` 转成 `{{host}}`。"""

        function_name = match.group(1)
        return f"{{{{{function_name}}}}}"

    @staticmethod
    def _replace_legacy_cache(match: re.Match) -> str:
        """把 `$cache{token}` 转成 `{{cache.token}}`。"""

        cache_key = match.group(1).strip()
        return f"{{{{cache.{cache_key}}}}}"
