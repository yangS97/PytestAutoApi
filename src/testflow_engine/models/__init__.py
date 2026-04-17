"""
测试引擎核心模型导出。

模型层负责定义“平台真源如何进入引擎、引擎如何返回结构化结果”。
后续 FastAPI、worker、报告、插件都应围绕这些模型扩展，而不是各自再造字段。
"""

from .core import (
    AssertionOperator,
    AssertionResult,
    AssertionSource,
    AssertionSpec,
    BodyType,
    CaseExecutionResult,
    CaseSource,
    ExtractionSource,
    ExtractionSpec,
    ExecutionContext,
    ExecutionStatus,
    HttpMethod,
    ReportSummary,
    RequestSpec,
    ResponseSnapshot,
    RunExecutionResult,
    SelectorType,
    StepExecutionResult,
    TestCaseDefinition,
    TestRunDefinition,
)

__all__ = [
    "AssertionOperator",
    "AssertionResult",
    "AssertionSource",
    "AssertionSpec",
    "BodyType",
    "CaseExecutionResult",
    "CaseSource",
    "ExtractionSource",
    "ExtractionSpec",
    "ExecutionContext",
    "ExecutionStatus",
    "HttpMethod",
    "ReportSummary",
    "RequestSpec",
    "ResponseSnapshot",
    "RunExecutionResult",
    "SelectorType",
    "StepExecutionResult",
    "TestCaseDefinition",
    "TestRunDefinition",
]
