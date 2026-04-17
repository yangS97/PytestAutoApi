"""
插件接口骨架。

插件的职责不是替代执行器，而是在关键生命周期节点做增强：
- 注入鉴权、变量、环境信息
- 采集日志、链路追踪、截图
- 把运行上下文同步回平台

这里先定义稳定 hook，后续实现可以在不破坏上层调用方的前提下逐步变强。
"""

from abc import ABC

from ..models import (
    CaseExecutionResult,
    ExecutionContext,
    ResponseSnapshot,
    RunExecutionResult,
    TestCaseDefinition,
    TestRunDefinition,
)


class EnginePlugin(ABC):
    """引擎插件基类，默认全部为 no-op。"""

    name = "unnamed-plugin"

    def before_run(self, run: TestRunDefinition, context: ExecutionContext) -> None:
        """run 开始前触发。"""

    def before_case(self, case: TestCaseDefinition, context: ExecutionContext) -> None:
        """case 执行前触发。"""

    def after_response(
        self,
        case: TestCaseDefinition,
        response: ResponseSnapshot,
        context: ExecutionContext,
    ) -> None:
        """响应返回后、断言开始前触发。"""

    def after_case(
        self,
        case: TestCaseDefinition,
        result: CaseExecutionResult,
        context: ExecutionContext,
    ) -> None:
        """case 收尾时触发。"""

    def after_run(self, result: RunExecutionResult, context: ExecutionContext) -> None:
        """run 完成后触发。"""
