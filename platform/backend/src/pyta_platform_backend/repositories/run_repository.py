"""run 仓储骨架。"""

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from pyta_platform_backend.schemas.run import (
    CreateRunRequest,
    ListRunsResponse,
    RunDetailResponse,
    RunStatus,
    RunSummaryResponse,
    UpdateRunStatusRequest,
)
from pyta_platform_backend.repositories.sqlite_support import (
    connect_sqlite,
    dump_datetime,
    dump_json,
    load_datetime,
    load_json,
)


@dataclass(frozen=True)
class RunRecord:
    """平台 run 主记录。"""

    run_id: str
    suite_id: str
    environment_id: Optional[str]
    environment_name: Optional[str]
    trigger_source: str
    requested_by: str
    payload: dict[str, object]
    status: RunStatus
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    status_message: Optional[str]


class InMemoryRunRepository:
    """内存版 run 仓储。"""

    def __init__(self) -> None:
        self._records: dict[str, RunRecord] = {}

    def create_pending_run(
        self,
        payload: CreateRunRequest,
        *,
        environment_name: Optional[str] = None,
    ) -> RunRecord:
        """创建一个处于 queued 状态的 run。"""

        run_id = uuid4().hex
        now = datetime.now(timezone.utc)
        record = RunRecord(
            run_id=run_id,
            suite_id=payload.suite_id,
            environment_id=payload.environment_id,
            environment_name=environment_name,
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
        """返回详情模型。"""

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

    def list_queued_records(self) -> list[RunRecord]:
        """返回当前仍处于 queued 的记录，供 dispatcher 重建待执行队列。"""

        return sorted(
            [item for item in self._records.values() if item.status == RunStatus.QUEUED],
            key=lambda item: item.created_at,
        )

    def update_status(
        self,
        run_id: str,
        payload: UpdateRunStatusRequest,
    ) -> Optional[RunDetailResponse]:
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
            environment_id=record.environment_id,
            environment_name=record.environment_name,
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
            environment_id=record.environment_id,
            environment_name=record.environment_name,
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

        summary_payload = cls._dump_model(cls._to_summary(record))
        return RunDetailResponse(
            **summary_payload,
            payload=deepcopy(record.payload),
            status_message=record.status_message,
        )

    @staticmethod
    def _dump_model(model) -> dict[str, object]:
        """兼容 Pydantic v1/v2 的 dump。"""

        if hasattr(model, "model_dump"):
            return model.model_dump()
        return model.dict()


class SqliteRunRepository(InMemoryRunRepository):
    """sqlite 版 run 仓储。

    这里不引入更重的 ORM，只把当前平台真正需要的 run 主记录
    落到一个轻量 sqlite 文件里，优先解决“服务一重启记录全丢”的问题。
    """

    def __init__(self, database_path: str) -> None:
        self._database_path = database_path
        self._connection = connect_sqlite(self._database_path)
        self._initialize_tables()

    def create_pending_run(
        self,
        payload: CreateRunRequest,
        *,
        environment_name: Optional[str] = None,
    ) -> RunRecord:
        """创建一个处于 queued 状态的 run。"""

        run_id = uuid4().hex
        now = datetime.now(timezone.utc)
        record = RunRecord(
            run_id=run_id,
            suite_id=payload.suite_id,
            environment_id=payload.environment_id,
            environment_name=environment_name,
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

        self._connection.execute(
            """
            INSERT INTO runs (
                run_id,
                suite_id,
                environment_id,
                environment_name,
                trigger_source,
                requested_by,
                payload_json,
                status,
                created_at,
                updated_at,
                started_at,
                finished_at,
                status_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._record_to_row(record),
        )
        self._connection.commit()

        return record

    def get_by_id(self, run_id: str) -> Optional[RunRecord]:
        """按 run_id 查询记录。"""

        row = self._connection.execute(
            """
            SELECT
                run_id,
                suite_id,
                environment_id,
                environment_name,
                trigger_source,
                requested_by,
                payload_json,
                status,
                created_at,
                updated_at,
                started_at,
                finished_at,
                status_message
            FROM runs
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()

        if row is None:
            return None
        return self._row_to_record(row)

    def list_runs(self, limit: int, offset: int) -> ListRunsResponse:
        """返回分页后的 run 列表。"""

        total = self._connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        rows = self._connection.execute(
            """
            SELECT
                run_id,
                suite_id,
                environment_id,
                environment_name,
                trigger_source,
                requested_by,
                payload_json,
                status,
                created_at,
                updated_at,
                started_at,
                finished_at,
                status_message
            FROM runs
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

        records = [self._row_to_record(row) for row in rows]
        return ListRunsResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=[self._to_summary(record) for record in records],
        )

    def list_queued_records(self) -> list[RunRecord]:
        """返回当前仍处于 queued 的记录，供 dispatcher 重建待执行队列。"""

        rows = self._connection.execute(
            """
            SELECT
                run_id,
                suite_id,
                environment_id,
                environment_name,
                trigger_source,
                requested_by,
                payload_json,
                status,
                created_at,
                updated_at,
                started_at,
                finished_at,
                status_message
            FROM runs
            WHERE status = ?
            ORDER BY created_at ASC
            """,
            (RunStatus.QUEUED.value,),
        ).fetchall()

        return [self._row_to_record(row) for row in rows]

    def update_status(
        self,
        run_id: str,
        payload: UpdateRunStatusRequest,
    ) -> Optional[RunDetailResponse]:
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
            environment_id=record.environment_id,
            environment_name=record.environment_name,
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

        self._connection.execute(
            """
            UPDATE runs
            SET
                suite_id = ?,
                environment_id = ?,
                environment_name = ?,
                trigger_source = ?,
                requested_by = ?,
                payload_json = ?,
                status = ?,
                created_at = ?,
                updated_at = ?,
                started_at = ?,
                finished_at = ?,
                status_message = ?
            WHERE run_id = ?
            """,
            (
                updated_record.suite_id,
                updated_record.environment_id,
                updated_record.environment_name,
                updated_record.trigger_source,
                updated_record.requested_by,
                dump_json(updated_record.payload),
                updated_record.status.value,
                dump_datetime(updated_record.created_at),
                dump_datetime(updated_record.updated_at),
                dump_datetime(updated_record.started_at),
                dump_datetime(updated_record.finished_at),
                updated_record.status_message,
                updated_record.run_id,
            ),
        )
        self._connection.commit()

        return self._to_detail(updated_record)

    def _initialize_tables(self) -> None:
        """初始化 runs 表。"""

        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                suite_id TEXT NOT NULL,
                environment_id TEXT,
                environment_name TEXT,
                trigger_source TEXT NOT NULL,
                requested_by TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                status_message TEXT
            )
            """
        )
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at DESC)"
        )
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_runs_suite_id ON runs(suite_id)"
        )
        self._connection.commit()

    @staticmethod
    def _record_to_row(record: RunRecord) -> tuple[object, ...]:
        """把 RunRecord 展平为 sqlite 行。"""

        return (
            record.run_id,
            record.suite_id,
            record.environment_id,
            record.environment_name,
            record.trigger_source,
            record.requested_by,
            dump_json(record.payload),
            record.status.value,
            dump_datetime(record.created_at),
            dump_datetime(record.updated_at),
            dump_datetime(record.started_at),
            dump_datetime(record.finished_at),
            record.status_message,
        )

    @staticmethod
    def _row_to_record(row) -> RunRecord:
        """把 sqlite 行还原为 RunRecord。"""

        return RunRecord(
            run_id=row["run_id"],
            suite_id=row["suite_id"],
            environment_id=row["environment_id"],
            environment_name=row["environment_name"],
            trigger_source=row["trigger_source"],
            requested_by=row["requested_by"],
            payload=load_json(row["payload_json"], default={}),
            status=RunStatus(row["status"]),
            created_at=load_datetime(row["created_at"]),
            updated_at=load_datetime(row["updated_at"]),
            started_at=load_datetime(row["started_at"]),
            finished_at=load_datetime(row["finished_at"]),
            status_message=row["status_message"],
        )
