"""平台管理页聚合服务。"""

from typing import Optional

from fastapi import HTTPException, status

from pyta_platform_backend.repositories.management_repository import (
    EnvironmentRecord,
    InMemoryManagementRepository,
)
from pyta_platform_backend.repositories.run_repository import InMemoryRunRepository
from pyta_platform_backend.schemas.management import (
    CaseSummaryResponse,
    CreateEnvironmentRequest,
    CreateEnvironmentResponse,
    DeleteEnvironmentResponse,
    EnvironmentDetailResponse,
    EnvironmentSummaryResponse,
    ScheduleSummaryResponse,
    SuiteSummaryResponse,
    UpdateEnvironmentRequest,
    UpdateEnvironmentResponse,
)
from pyta_platform_backend.schemas.run import RunSummaryResponse


class ManagementService:
    """管理页聚合服务。

    这层负责把管理目录仓储中的静态骨架数据，与 run 主真源中的最近活动时间，
    整理成前端页面可直接消费的结构。
    """

    def __init__(
        self,
        repository: InMemoryManagementRepository,
        run_repository: InMemoryRunRepository,
    ) -> None:
        self._repository = repository
        self._run_repository = run_repository

    def list_cases(self) -> list[CaseSummaryResponse]:
        """返回用例目录。"""

        return [
            CaseSummaryResponse(
                id=record.id,
                name=record.name,
                module=record.module,
                method=record.method,
                priority=record.priority,
                status=record.status,
            )
            for record in self._repository.list_cases()
        ]

    def list_suites(self) -> list[SuiteSummaryResponse]:
        """返回套件目录。"""

        latest_run_by_suite = self._build_latest_run_index()
        return [
            SuiteSummaryResponse(
                id=record.id,
                name=record.name,
                case_count=record.case_count,
                last_run=self._format_last_run(latest_run_by_suite.get(record.id)),
                schedule=record.schedule,
            )
            for record in self._repository.list_suites()
        ]

    def list_environments(self) -> list[EnvironmentSummaryResponse]:
        """返回环境目录。"""

        return [
            self._to_environment_summary(record)
            for record in self._repository.list_environments()
        ]

    def get_environment_detail(self, environment_id: str) -> EnvironmentDetailResponse:
        """返回单个环境详情。"""

        record = self._get_environment_or_404(environment_id)
        return self._to_environment_detail(record)

    def create_environment(self, payload: CreateEnvironmentRequest) -> CreateEnvironmentResponse:
        """创建新的环境目录。"""

        name = self._require_text(payload.name, field_name="name")
        base_url = self._normalize_base_url(payload.base_url)
        auth_mode = self._require_text(payload.auth_mode, field_name="auth_mode")
        normalized_status = self._normalize_status(payload.status)

        try:
            record = self._repository.create_environment(
                name=name,
                base_url=base_url,
                auth_mode=auth_mode,
                status=normalized_status,
                variables=dict(payload.variables),
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc

        return CreateEnvironmentResponse(
            **self._dump_model(self._to_environment_detail(record))
        )

    def update_environment(
        self,
        environment_id: str,
        payload: UpdateEnvironmentRequest,
    ) -> UpdateEnvironmentResponse:
        """更新环境目录。

        使用 patch 语义是为了给后续环境资源扩容留余地：
        即使前端这轮只编辑少数字段，也不会误伤未来补上的变量或密钥引用。
        """

        existing = self._get_environment_or_404(environment_id)
        name = (
            self._require_text(payload.name, field_name="name")
            if payload.name is not None
            else existing.name
        )
        base_url = (
            self._normalize_base_url(payload.base_url)
            if payload.base_url is not None
            else existing.base_url
        )
        auth_mode = (
            self._require_text(payload.auth_mode, field_name="auth_mode")
            if payload.auth_mode is not None
            else existing.auth_mode
        )
        normalized_status = (
            self._normalize_status(payload.status)
            if payload.status is not None
            else existing.status
        )
        variables = dict(existing.variables if payload.variables is None else payload.variables)

        try:
            updated = self._repository.update_environment(
                environment_id,
                name=name,
                base_url=base_url,
                auth_mode=auth_mode,
                status=normalized_status,
                variables=variables,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc

        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"environment 不存在: {environment_id}",
            )

        return UpdateEnvironmentResponse(
            **self._dump_model(self._to_environment_detail(updated))
        )

    def delete_environment(self, environment_id: str) -> DeleteEnvironmentResponse:
        """删除环境目录。"""

        deleted = self._repository.delete_environment(environment_id)
        if deleted is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"environment 不存在: {environment_id}",
            )

        return DeleteEnvironmentResponse(
            **self._dump_model(self._to_environment_summary(deleted))
        )

    def list_schedules(self) -> list[ScheduleSummaryResponse]:
        """返回调度目录。"""

        latest_run_by_suite = self._build_latest_run_index()
        return [
            ScheduleSummaryResponse(
                id=record.id,
                name=record.name,
                cron=record.cron,
                target=f"suite/{record.target_suite_id}",
                environment_id=record.environment_id,
                environment_name=self._resolve_environment_name(record.environment_id),
                last_run=self._format_last_run(latest_run_by_suite.get(record.target_suite_id)),
                status=record.status,
            )
            for record in self._repository.list_schedules()
        ]

    def _build_latest_run_index(self) -> dict[str, RunSummaryResponse]:
        """按 suite_id 收口最近一次 run。"""

        latest: dict[str, RunSummaryResponse] = {}
        for item in self._run_repository.list_runs(limit=1000, offset=0).items:
            if item.suite_id not in latest:
                latest[item.suite_id] = item
        return latest

    def _get_environment_or_404(self, environment_id: str) -> EnvironmentRecord:
        """读取环境，不存在则抛 404。"""

        record = self._repository.get_environment_by_id(environment_id)
        if record is not None:
            return record

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"environment 不存在: {environment_id}",
        )

    def _resolve_environment_name(self, environment_id: str) -> Optional[str]:
        """按环境 ID 解析展示名称。"""

        environment = self._repository.get_environment_by_id(environment_id)
        if environment is None:
            return None
        return environment.name

    @staticmethod
    def _to_environment_summary(record: EnvironmentRecord) -> EnvironmentSummaryResponse:
        """把仓储记录映射成环境摘要。"""

        return EnvironmentSummaryResponse(
            id=record.id,
            name=record.name,
            base_url=record.base_url,
            auth_mode=record.auth_mode,
            status=record.status,
        )

    @classmethod
    def _to_environment_detail(cls, record: EnvironmentRecord) -> EnvironmentDetailResponse:
        """把仓储记录映射成环境详情。"""

        summary_payload = cls._dump_model(cls._to_environment_summary(record))
        return EnvironmentDetailResponse(
            **summary_payload,
            variables=dict(record.variables),
        )

    @staticmethod
    def _dump_model(model) -> dict[str, object]:
        """兼容 Pydantic v1/v2 的 dump。"""

        if hasattr(model, "model_dump"):
            return model.model_dump()
        return model.dict()

    @staticmethod
    def _format_last_run(run: Optional[RunSummaryResponse]) -> str:
        """格式化最近运行时间。"""

        if run is None:
            return "尚未执行"

        timestamp = run.started_at or run.created_at
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _require_text(value: str, field_name: str) -> str:
        """校验并清理基础文本字段。"""

        normalized = str(value or "").strip()
        if normalized:
            return normalized

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} 不能为空",
        )

    @classmethod
    def _normalize_base_url(cls, base_url: str) -> str:
        """校验并清理 base_url。"""

        normalized = cls._require_text(base_url, field_name="base_url").rstrip("/")
        if normalized.startswith("http://") or normalized.startswith("https://"):
            return normalized

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="base_url 必须以 http:// 或 https:// 开头",
        )

    @staticmethod
    def _normalize_status(status_value: str) -> str:
        """限制环境状态到当前前端可识别的最小集合。"""

        normalized = str(status_value or "draft").strip().lower() or "draft"
        if normalized in {"online", "draft"}:
            return normalized

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status 仅支持 online / draft",
        )
