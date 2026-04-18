"""仪表盘业务服务。

这个服务先只做一件事：
把 run 仓储里的真实状态，整理成首页能够直接消费的结构。

之所以单独做 service，而不是在路由里拼字典，是为了后续加更多统计项时，
仍然能保持 API 层足够薄。
"""

from pyta_platform_backend.repositories.run_repository import InMemoryRunRepository
from pyta_platform_backend.schemas.dashboard import (
    DashboardFocusItemResponse,
    DashboardMetricResponse,
    DashboardOverviewResponse,
    DashboardRecentRunResponse,
)
from pyta_platform_backend.schemas.run import RunStatus


class DashboardService:
    """首页聚合服务。"""

    def __init__(self, repository: InMemoryRunRepository) -> None:
        self._repository = repository

    def get_overview(self) -> DashboardOverviewResponse:
        """构造首页总览。

        第一阶段先用真实 run 数据 + 少量静态重点事项拼出首页，优先打通真实链路。
        """

        records = self._repository.list_runs(limit=5, offset=0)
        all_records = self._repository.list_runs(limit=1000, offset=0)

        metrics = [
            DashboardMetricResponse(
                key="runs",
                label="累计运行",
                value=str(all_records.total),
                description="平台主真源里已经登记的运行次数",
                trend=f"最近 {len(records.items)} 条可在结果页查看",
            ),
            DashboardMetricResponse(
                key="queued",
                label="排队中",
                value=str(sum(1 for item in all_records.items if item.status == RunStatus.QUEUED)),
                description="已经创建但尚未开始执行的 run",
                trend="API 只记账与投递，不在请求线程里执行",
            ),
            DashboardMetricResponse(
                key="running",
                label="执行中",
                value=str(sum(1 for item in all_records.items if item.status == RunStatus.RUNNING)),
                description="当前仍在 worker 中运行的 run",
                trend="适合后续接实时刷新或 websocket",
            ),
            DashboardMetricResponse(
                key="failed",
                label="失败数",
                value=str(sum(1 for item in all_records.items if item.status == RunStatus.FAILED)),
                description="用于快速发现最近需要优先排查的问题",
                trend="成功/失败趋势后续可扩到更完整统计",
            ),
        ]

        focus_items = [
            DashboardFocusItemResponse(
                id="focus-platform-truth",
                title="平台主真源已经落地",
                owner="测试平台",
                status="stable",
                summary="运行记录已开始通过平台主真源持久化，不再只停留在页面 mock。",
            ),
            DashboardFocusItemResponse(
                id="focus-worker-boundary",
                title="执行边界继续收紧",
                owner="后端编排",
                status="attention",
                summary="API 进程只创建和投递任务，真实长任务执行仍需继续完善 worker 入口。",
            ),
            DashboardFocusItemResponse(
                id="focus-legacy-migration",
                title="legacy YAML 迁移仍在进行",
                owner="兼容层",
                status="planned",
                summary="当前已能桥接第一层结构，后续还要继续补依赖、缓存替换和更完整断言。",
            ),
        ]

        recent_runs = [
            DashboardRecentRunResponse(
                id=item.run_id,
                name=f"运行 {item.run_id[:8]}",
                target=item.suite_id,
                status=self._map_run_status(item.status),
                started_at=self._format_time(item.started_at or item.created_at),
                duration=self._format_duration(item.created_at, item.finished_at),
                starter=item.requested_by,
                raw_status=item.status.value,
            )
            for item in records.items[:3]
        ]

        return DashboardOverviewResponse(
            metrics=metrics,
            focus_items=focus_items,
            recent_runs=recent_runs,
        )

    @staticmethod
    def _map_run_status(status: RunStatus) -> str:
        """把后端原始状态映射到首页更易读的展示状态。"""

        if status == RunStatus.RUNNING:
            return "running"
        if status == RunStatus.FAILED:
            return "warning"
        if status == RunStatus.SUCCEEDED:
            return "success"
        return "running" if status == RunStatus.QUEUED else "warning"

    @staticmethod
    def _format_time(value) -> str:
        """把 datetime 转成前端可直接展示的字符串。"""

        return value.strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def _format_duration(cls, created_at, finished_at) -> str:
        """把 run 耗时格式化为简单文案。

        当前没有真实 worker 开始/结束时间链路，所以第一阶段先退化为：
        - 已完成：按 created_at 到 finished_at 计算
        - 未完成：展示“执行中”
        """

        if finished_at is None:
            return "执行中"
        seconds = int((finished_at - created_at).total_seconds())
        minutes, remain_seconds = divmod(seconds, 60)
        return f"{minutes}m {remain_seconds}s"
