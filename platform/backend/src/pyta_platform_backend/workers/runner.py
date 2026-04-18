"""内存版 worker runner。

这个 runner 的目标不是替代正式队列系统，而是先把下面这条链路做实：

create run -> dispatch -> worker consume -> update status

只要这条链路成立，后续无论替换成进程池、APScheduler 触发、还是更重的消息队列，
都不会再回到“API 线程自己跑长任务”的旧问题。
"""

from copy import deepcopy
from dataclasses import dataclass
from typing import Callable, Optional

from pyta_platform_backend.schemas.run import RunDetailResponse, RunStatus, UpdateRunStatusRequest
from pyta_platform_backend.services.run_service import RunService
from pyta_platform_backend.workers.dispatcher import DispatchTask, MemoryRunDispatcher
from testflow_engine import (
    BootstrapAuthPlugin,
    CallableTransport,
    HttpxTransport,
    LegacyCachePlugin,
    LegacyYamlCompatLoader,
    ResponseSnapshot,
    TestFlowEngine,
    TestRunDefinition,
)
from testflow_engine.models import ExecutionStatus


@dataclass(frozen=True)
class WorkerExecutionResult:
    """worker 执行后的最小回执。"""

    status: RunStatus
    status_message: Optional[str] = None


class MemoryWorkerRunner:
    """最小可运行的内存 worker。

    它做的事情很克制：
    1. 从 dispatcher 拿任务
    2. 先把 run 标记为 running
    3. 调一个很薄的 handler 模拟真实执行
    4. 根据结果回写 succeeded / failed
    """

    def __init__(
        self,
        dispatcher: MemoryRunDispatcher,
        run_service: RunService,
        handler: Optional[Callable[[DispatchTask], WorkerExecutionResult]] = None,
    ) -> None:
        self._dispatcher = dispatcher
        self._run_service = run_service
        self._handler = handler or self._default_handler

    def run_next(self) -> Optional[RunDetailResponse]:
        """消费一个任务。

        如果当前没有任务，返回 None；这样上层调度器或脚本可以很容易判断“是否有活可干”。
        """

        task = self._dispatcher.pull_next()
        if task is None:
            return None

        self._run_service.update_run_status(
            task.run_id,
            UpdateRunStatusRequest(
                status=RunStatus.RUNNING,
                status_message="memory worker started",
            ),
        )

        try:
            result = self._handler(task)
            return self._run_service.update_run_status(
                task.run_id,
                UpdateRunStatusRequest(
                    status=result.status,
                    status_message=result.status_message,
                ),
            )
        except Exception as exc:  # pragma: no cover - 错误路径由测试覆盖
            return self._run_service.update_run_status(
                task.run_id,
                UpdateRunStatusRequest(
                    status=RunStatus.FAILED,
                    status_message=str(exc),
                ),
            )

    @staticmethod
    def _default_handler(task: DispatchTask) -> WorkerExecutionResult:
        """默认 handler。

        这里不再只是返回一个固定成功值，而是优先尝试真正执行第一阶段最重要的演示链路：
        `legacy YAML -> 新引擎 -> 结果汇总`

        如果任务本身不是 legacy YAML 模式，再退回最简单的成功路径。
        """

        execution_mode = str(task.payload.get("execution_mode") or "").strip().lower()
        if execution_mode == "standard_run":
            return MemoryWorkerRunner._run_standard_run_task(task)
        if execution_mode == "legacy_yaml":
            return MemoryWorkerRunner._run_legacy_yaml_task(task)

        return WorkerExecutionResult(
            status=RunStatus.SUCCEEDED,
            status_message=f"memory worker finished suite {task.suite_id}",
        )

    @staticmethod
    def _run_legacy_yaml_task(task: DispatchTask) -> WorkerExecutionResult:
        """执行 legacy YAML 示例任务。

        这一层用最小代价把“历史资产迁移”和“新引擎执行”串起来：
        1. 从 payload 里读取 legacy YAML 路径
        2. 用 compat loader 转成新 RunDefinition
        3. 用可控的 mock transport 跑完整个引擎
        4. 再把摘要转成平台 run 状态

        这样做的好处是：
        - 不依赖真实网络
        - 不依赖真实环境
        - 但又不是假装执行，而是真正走过了新引擎主链路
        """

        yaml_path = str(task.payload.get("legacy_yaml_path") or "").strip()
        if not yaml_path:
            raise ValueError("legacy_yaml 模式缺少 legacy_yaml_path")

        loader = LegacyYamlCompatLoader()
        document = loader.load_from_path(yaml_path)
        run_definition = loader.to_run_definition(document, run_name=f"legacy:{yaml_path}")
        variables = MemoryWorkerRunner._merge_environment_variables(
            task=task,
            variables=dict(task.payload.get("variables") or {}),
        )
        if hasattr(run_definition, "model_copy"):
            run_definition = run_definition.model_copy(
                update={"variables": variables},
                deep=True,
            )
        else:
            run_definition = run_definition.copy(
                update={"variables": variables},
                deep=True,
            )

        engine = MemoryWorkerRunner._build_engine_for_task(task)
        result = engine.execute_run(run_definition)
        summary = result.summary
        status = MemoryWorkerRunner._map_engine_status(result.status)
        return WorkerExecutionResult(
            status=status,
            status_message=(
                f"legacy yaml executed from {yaml_path}: total={summary.total} "
                f"passed={summary.passed} failed={summary.failed} "
                f"errors={summary.errors} skipped={summary.skipped}"
            ),
        )

    @staticmethod
    def _run_standard_run_task(task: DispatchTask) -> WorkerExecutionResult:
        """执行已经标准化的新框架 run。

        这是迁移的正确方向：
        老用例只是迁移输入，真正执行时应尽量变成 `TestRunDefinition` 这种新模型。
        """

        raw_run_definition = dict(task.payload.get("run_definition") or {})
        if not raw_run_definition:
            raise ValueError("standard_run 模式缺少 run_definition")

        if hasattr(TestRunDefinition, "model_validate"):
            run_definition = TestRunDefinition.model_validate(raw_run_definition)
        else:
            run_definition = TestRunDefinition.parse_obj(raw_run_definition)

        merged_variables = MemoryWorkerRunner._merge_environment_variables(
            task=task,
            variables=dict(getattr(run_definition, "variables", {}) or {}),
        )
        if hasattr(run_definition, "model_copy"):
            run_definition = run_definition.model_copy(
                update={"variables": merged_variables},
                deep=True,
            )
        else:
            run_definition = run_definition.copy(
                update={"variables": merged_variables},
                deep=True,
            )

        engine = MemoryWorkerRunner._build_engine_for_task(task)
        result = engine.execute_run(run_definition)
        summary = result.summary
        status = MemoryWorkerRunner._map_engine_status(result.status)
        return WorkerExecutionResult(
            status=status,
            status_message=(
                f"standard run executed: total={summary.total} "
                f"passed={summary.passed} failed={summary.failed} "
                f"errors={summary.errors} skipped={summary.skipped}"
            ),
        )

    @staticmethod
    def _build_mock_response(task: DispatchTask, case_id: str) -> ResponseSnapshot:
        """从任务 payload 构造一个可预测的 mock 响应。

        为了让同一个 legacy YAML 文件里的多个 case 都能跑通，
        payload 支持两级配置：

        1. `mock_response`：默认响应
        2. `mock_case_responses[case_id]`：指定 case 的覆盖响应
        """

        default_response = dict(task.payload.get("mock_response") or {})
        per_case_responses = dict(task.payload.get("mock_case_responses") or {})
        case_response = dict(per_case_responses.get(case_id) or {})

        merged: dict[str, object] = {
            **default_response,
            **case_response,
        }
        return ResponseSnapshot(
            status_code=int(merged.get("status_code") or 200),
            headers=dict(merged.get("headers") or {}),
            body=merged.get("body"),
            elapsed_ms=float(merged.get("elapsed_ms") or 1.0),
            request_id=str(merged.get("request_id")) if merged.get("request_id") else None,
        )

    @staticmethod
    def _build_engine_for_task(task: DispatchTask) -> TestFlowEngine:
        """按任务配置构造执行引擎。

        当前支持两种 transport 模式：
        - mock：适合结构验证和不依赖真实网络的演示
        - live：适合真正验证迁移后的用例是否还能打到目标系统
        """

        transport_mode = str(task.payload.get("transport_mode") or "mock").strip().lower()
        plugins = [LegacyCachePlugin()]

        if "auth_bootstrap" in dict(task.payload.get("variables") or {}):
            plugins.append(BootstrapAuthPlugin())

        if transport_mode == "live":
            return TestFlowEngine(
                transport=HttpxTransport(),
                plugins=plugins,
            )

        return TestFlowEngine(
            transport=CallableTransport(
                lambda request, context, case: MemoryWorkerRunner._build_mock_response(
                    task,
                    case.case_id,
                )
            ),
            plugins=plugins,
        )

    @staticmethod
    def _merge_environment_variables(
        task: DispatchTask,
        variables: dict[str, object],
    ) -> dict[str, object]:
        """把 payload 中的 environment 快照并入执行变量。"""

        merged = deepcopy(variables)
        environment = dict(task.payload.get("environment") or {})
        if not environment:
            return merged

        merged.setdefault("environment", environment)
        if not merged.get("host") and environment.get("base_url"):
            merged["host"] = environment["base_url"]
        return merged

    @staticmethod
    def _map_engine_status(status: ExecutionStatus) -> RunStatus:
        """把引擎执行状态映射为平台 run 状态。"""

        if status == ExecutionStatus.PASSED:
            return RunStatus.SUCCEEDED
        if status == ExecutionStatus.SKIPPED:
            return RunStatus.SUCCEEDED
        return RunStatus.FAILED
