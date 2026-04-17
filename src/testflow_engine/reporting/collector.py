"""
报告聚合骨架。

目标不是立刻替代 Allure，而是先把执行结果整理成统一结构，
让平台页面、异步 worker、legacy 兼容链路都能消费同一份摘要数据。
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from ..models import (
    CaseExecutionResult,
    ExecutionStatus,
    ReportSummary,
    RunExecutionResult,
)


class ReportSnapshot(BaseModel):
    """报告快照，适合作为 API 返回值或写入数据库的中间结构。"""

    run_id: str
    generated_at: datetime
    summary: ReportSummary
    cases: List[CaseExecutionResult] = Field(default_factory=list)


class ReportCollector:
    """收集执行结果并构造摘要。"""

    def build_summary(self, cases: List[CaseExecutionResult]) -> ReportSummary:
        """根据 case 结果统计汇总数据。"""

        summary = ReportSummary(total=len(cases))
        for case in cases:
            if case.status == ExecutionStatus.PASSED:
                summary.passed += 1
            elif case.status == ExecutionStatus.FAILED:
                summary.failed += 1
            elif case.status == ExecutionStatus.ERROR:
                summary.errors += 1
            elif case.status == ExecutionStatus.SKIPPED:
                summary.skipped += 1
        return summary

    def build_snapshot(self, result: RunExecutionResult) -> ReportSnapshot:
        """把 run 结果转成可持久化/可展示的报告快照。"""

        return ReportSnapshot(
            run_id=result.run_id,
            generated_at=datetime.utcnow(),
            summary=result.summary,
            cases=result.cases,
        )
