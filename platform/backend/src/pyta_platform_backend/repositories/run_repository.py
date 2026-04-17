"""run 仓储骨架。"""

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import uuid4

from pyta_platform_backend.schemas.run import (
    CreateRunRequest,
    ListRunsResponse,
    RunDetailResponse,
    RunStatus,
    RunSummaryResponse,
    UpdateRunStatusRequest,
)


@dataclass(frozen=True)
class RunRecord:
    """平台 run 主记录。

    第一阶段先用内存仓储占位，后续迁移到数据库时，只需要替换仓储实现，
    service 和 API 不应该感知底层存储细节。
    """

    run_id: str
    suite_id: str
    trigger_source: str
    requested_by: str
    payload: Dict[str, object]
    status: RunStatus
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    status_message: Optional[str]


class InMemoryRunRepository:
    """内存版 run 仓储。

    这是骨架阶段的最小实现，主要用于说明“平台是主真源”这件事：
    即使还没接数据库，也先通过仓储对象承接写入动作，而不是直接在路由里拼字典。
    """

    def __init__(self) -> None:
        self._records: Dict[str, RunRecord] = {}

    def create_pending_run(self, payload: CreateRunRequest) -> RunRecord:
        """创建一个处于 queued 状态的 run。"""

        run_id = uuid4().hex
        now = datetime.now(timezone.utc)
        record = RunRecord(
            run_id=run_id,
            suite_id=payload.suite_id,
            trigger_source=payload.trigger_source,
            requested_by=payload.requested_by,
            payload=deepcopy(payload.payload),
            status=RunStatus.QUEUED,
            created_at=now,
            updated_at=now,
            started_at=None,
            finished_at=None,
            status_message=None,
        )
        self._records[run_id] = record
        return record

    def get_by_id(self, run_id: str) -> Optional[RunRecord]:
        """按 run_id 查询记录。"""

        return self._records.get(run_id)

    def get_detail(self, run_id: str) -> Optional[RunDetailResponse]:
        """返回详情模型。

        仓储层直接返回 schema 是当前骨架阶段的折中做法：
        一方面减少模板代码；另一方面也能让 API/service 先把闭环走通。
        后续若实体和响应模型明显分离，再继续抽 mapper。
        """

        record = self.get_by_id(run_id)
        if record is None:
            return None
        return self._to_detail(record)

    def list_runs(self, limit: int, offset: int) -> ListRunsResponse:
        """返回分页后的 run 列表。"""

        ordered_records = sorted(
            self._records.values(),
            key=lambda item: item.created_at,
            reverse=True,
        )
        sliced = ordered_records[offset : offset + limit]
        return ListRunsResponse(
            total=len(ordered_records),
            limit=limit,
            offset=offset,
            items=[self._to_summary(record) for record in sliced],
        )

    def update_status(self, run_id: str, payload: UpdateRunStatusRequest) -> Optional[RunDetailResponse]:
        """更新 run 状态并返回更新后的详情。"""

        record = self.get_by_id(run_id)
        if record is None:
            return None

        now = datetime.now(timezone.utc)
        started_at = record.started_at
        finished_at = record.finished_at

        if payload.status == RunStatus.RUNNING and started_at is None:
            started_at = now
            finished_at = None
        elif payload.status in {RunStatus.SUCCEEDED, RunStatus.FAILED}:
            if started_at is None:
                started_at = now
            finished_at = now

        updated_record = RunRecord(
            run_id=record.run_id,
            suite_id=record.suite_id,
            trigger_source=record.trigger_source,
            requested_by=record.requested_by,
            payload=deepcopy(record.payload),
            status=payload.status,
            created_at=record.created_at,
            updated_at=now,
            started_at=started_at,
            finished_at=finished_at,
            status_message=payload.status_message,
        )
        self._records[run_id] = updated_record
        return self._to_detail(updated_record)

    @staticmethod
    def _to_summary(record: RunRecord) -> RunSummaryResponse:
        """把仓储记录转成列表项。"""

        return RunSummaryResponse(
            run_id=record.run_id,
            suite_id=record.suite_id,
            trigger_source=record.trigger_source,
            requested_by=record.requested_by,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
            started_at=record.started_at,
            finished_at=record.finished_at,
        )

    @classmethod
    def _to_detail(cls, record: RunRecord) -> RunDetailResponse:
        """把仓储记录转成详情对象。"""

        summary = cls._to_summary(record)
        summary_payload = summary.model_dump() if hasattr(summary, "model_dump") else summary.dict()
        return RunDetailResponse(
            **summary_payload,
            payload=deepcopy(record.payload),
            status_message=record.status_message,
        )
