"""
测试执行器骨架。

执行链路固定为：
run -> case -> transport -> assertion -> report

这条链路是新引擎最核心的主干，后续无论挂 FastAPI 接口、异步 worker、
还是平台 UI 触发执行，都应该尽量复用这里，而不是复制一套流程。
"""

from datetime import datetime

from ..assertions import AssertionEngine
from .transport import TransportAdapter, TransportNotConfiguredError
from .rendering import RequestTemplateRenderer
from ..models import (
    CaseExecutionResult,
    ExecutionContext,
    ExecutionStatus,
    ExtractionSource,
    RunExecutionResult,
    StepExecutionResult,
    TestCaseDefinition,
    TestRunDefinition,
)
from ..plugins import EnginePlugin
from ..reporting import ReportCollector


class TestFlowEngine:
    """新测试引擎主执行器。"""

    def __init__(
        self,
        transport: TransportAdapter = None,
        assertion_engine: AssertionEngine = None,
        plugins=None,
        report_collector: ReportCollector = None,
        request_renderer: RequestTemplateRenderer = None,
    ) -> None:
        self.transport = transport
        self.assertion_engine = assertion_engine or AssertionEngine()
        self.plugins = list(plugins or [])
        self.report_collector = report_collector or ReportCollector()
        self.request_renderer = request_renderer or RequestTemplateRenderer()

    def execute_run(self, run: TestRunDefinition) -> RunExecutionResult:
        """执行整个 run，并返回聚合结果。"""

        started_at = datetime.utcnow()
        context = ExecutionContext(run_id=run.run_id, variables=dict(run.variables))
        for plugin in self.plugins:
            plugin.before_run(run=run, context=context)

        case_results = []
        for case in run.cases:
            case_results.append(self.execute_case(case=case, context=context))

        summary = self.report_collector.build_summary(case_results)
        status = self._resolve_run_status(summary=summary)
        result = RunExecutionResult(
            run_id=run.run_id,
            name=run.name,
            status=status,
            cases=case_results,
            summary=summary,
            started_at=started_at,
            finished_at=datetime.utcnow(),
        )
        for plugin in self.plugins:
            plugin.after_run(result=result, context=context)
        return result

    def execute_case(self, case: TestCaseDefinition, context: ExecutionContext) -> CaseExecutionResult:
        """执行单个 case。"""

        started_at = datetime.utcnow()
        for plugin in self.plugins:
            plugin.before_case(case=case, context=context)

        if not case.enabled:
            result = CaseExecutionResult(
                case_id=case.case_id,
                title=case.title,
                status=ExecutionStatus.SKIPPED,
                steps=[],
                started_at=started_at,
                finished_at=datetime.utcnow(),
            )
            self._notify_after_case(case=case, result=result, context=context)
            return result

        try:
            if self.transport is None:
                raise TransportNotConfiguredError("TestFlowEngine 尚未配置 transport")

            # 执行器先把运行时变量渲染进请求，再把“最终请求”交给 transport。
            # 这样 transport 只负责网络发送，不需要知道模板、上下文、平台变量规则。
            rendered_request = self.request_renderer.render(request=case.request, context=context)
            response = self.transport.send(request=rendered_request, context=context, case=case)
            for plugin in self.plugins:
                plugin.after_response(case=case, response=response, context=context)
            self._apply_extractors(case=case, response=response, context=context)

            assertion_results = self.assertion_engine.evaluate_all(
                assertions=case.assertions,
                response=response,
                context=context,
            )
            step_status = self._resolve_step_status(assertion_results)
            step = StepExecutionResult(
                name="request",
                status=step_status,
                response=response,
                assertions=assertion_results,
                started_at=started_at,
                finished_at=datetime.utcnow(),
            )
            result = CaseExecutionResult(
                case_id=case.case_id,
                title=case.title,
                status=step_status,
                steps=[step],
                started_at=started_at,
                finished_at=datetime.utcnow(),
            )
        except Exception as exc:  # pragma: no cover - 错误路径由结构骨架兜底
            result = CaseExecutionResult(
                case_id=case.case_id,
                title=case.title,
                status=ExecutionStatus.ERROR,
                steps=[
                    StepExecutionResult(
                        name="request",
                        status=ExecutionStatus.ERROR,
                        error=str(exc),
                        started_at=started_at,
                        finished_at=datetime.utcnow(),
                    )
                ],
                error=str(exc),
                started_at=started_at,
                finished_at=datetime.utcnow(),
            )

        self._notify_after_case(case=case, result=result, context=context)
        return result

    def _notify_after_case(
        self,
        case: TestCaseDefinition,
        result: CaseExecutionResult,
        context: ExecutionContext,
    ) -> None:
        """统一处理 after_case，避免多个出口漏调插件。"""

        for plugin in self.plugins:
            plugin.after_case(case=case, result=result, context=context)

    def _apply_extractors(
        self,
        case: TestCaseDefinition,
        response,
        context: ExecutionContext,
    ) -> None:
        """执行标准化变量提取。

        这是新框架里对“上一条请求产出的值，后续请求还要继续用”的正式支持。
        第一阶段先覆盖最常见的场景：
        - 从响应体里提取 ID / token / code
        - 从响应头里提取追踪信息
        - 把结果写到 `context.variables` 的指定路径
        """

        for extractor in case.extractors:
            actual = self._resolve_extractor_value(extractor=extractor, response=response)
            self._write_context_value(context=context, target=extractor.target, value=actual)

    def _resolve_extractor_value(self, extractor, response):
        """根据提取规则从响应里取值。"""

        if extractor.source == ExtractionSource.STATUS_CODE:
            return response.status_code
        if extractor.source == ExtractionSource.RESPONSE_HEADERS:
            return self.assertion_engine._extract_value(
                source=response.headers,
                selector=extractor.selector,
                selector_type=extractor.selector_type,
            )
        return self.assertion_engine._extract_value(
            source=response.body,
            selector=extractor.selector,
            selector_type=extractor.selector_type,
            response=response,
        )

    @staticmethod
    def _write_context_value(context: ExecutionContext, target: str, value) -> None:
        """把提取值写回上下文变量。

        target 用点路径表示，例如：
        - `cache.persona_id`
        - `auth.login_code`
        - `runtime.last_status`
        """

        if not target:
            return

        parts = [part for part in target.split(".") if part]
        if not parts:
            return

        current = context.variables
        for part in parts[:-1]:
            next_value = current.get(part)
            if not isinstance(next_value, dict):
                next_value = {}
                current[part] = next_value
            current = next_value
        current[parts[-1]] = value

    @staticmethod
    def _resolve_step_status(assertion_results) -> ExecutionStatus:
        """根据断言结果计算步骤状态。"""

        for result in assertion_results:
            if result.status != ExecutionStatus.PASSED:
                return ExecutionStatus.FAILED
        return ExecutionStatus.PASSED

    @staticmethod
    def _resolve_run_status(summary) -> ExecutionStatus:
        """根据 summary 计算 run 状态。"""

        if summary.errors:
            return ExecutionStatus.ERROR
        if summary.failed:
            return ExecutionStatus.FAILED
        if summary.passed == 0 and summary.skipped == summary.total:
            return ExecutionStatus.SKIPPED
        return ExecutionStatus.PASSED
