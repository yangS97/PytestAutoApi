"""
testflow_engine 包对外导出入口。

这里集中暴露骨架阶段最重要的抽象，方便上层平台、FastAPI 接口层
以及后续 worker/调度模块直接 import 使用。
"""

from .assertions import AssertionEngine
from .compat import LegacyYamlCompatLoader, LegacyYamlDocument
from .executor import (
    CallableTransport,
    HttpxTransport,
    InMemoryScheduler,
    MissingTemplateVariableError,
    RequestTemplateRenderer,
    ScheduledJob,
    TestFlowEngine,
    TransportAdapter,
    TransportNotConfiguredError,
)
from .models import (
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
from .plugins import BootstrapAuthPlugin, EnginePlugin, LegacyCachePlugin
from .reporting import ReportCollector, ReportSnapshot

__all__ = [
    "AssertionEngine",
    "AssertionOperator",
    "AssertionResult",
    "AssertionSource",
    "AssertionSpec",
    "BodyType",
    "BootstrapAuthPlugin",
    "CallableTransport",
    "CaseExecutionResult",
    "CaseSource",
    "ExtractionSource",
    "ExtractionSpec",
    "EnginePlugin",
    "ExecutionContext",
    "ExecutionStatus",
    "HttpxTransport",
    "HttpMethod",
    "InMemoryScheduler",
    "LegacyYamlCompatLoader",
    "LegacyCachePlugin",
    "LegacyYamlDocument",
    "MissingTemplateVariableError",
    "ReportCollector",
    "ReportSnapshot",
    "ReportSummary",
    "RequestTemplateRenderer",
    "RequestSpec",
    "ResponseSnapshot",
    "RunExecutionResult",
    "ScheduledJob",
    "SelectorType",
    "StepExecutionResult",
    "TestCaseDefinition",
    "TestFlowEngine",
    "TestRunDefinition",
    "TransportAdapter",
    "TransportNotConfiguredError",
]
