"""run 相关 schema。"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    """平台 run 生命周期状态。"""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class CreateRunRequest(BaseModel):
    """创建 run 的最小请求体。"""

    suite_id: str = Field(..., description="要执行的测试套件或计划标识")
    environment_id: Optional[str] = Field(None, description="要使用的环境资源 ID")
    trigger_source: str = Field("manual", description="触发来源，例如 manual / scheduler")
    requested_by: str = Field("platform-user", description="请求发起者")
    payload: dict[str, Any] = Field(default_factory=dict, description="运行时附加参数")


class CreateRunResponse(BaseModel):
    """创建 run 后返回给调用方的确认信息。"""

    run_id: str
    status: RunStatus
    dispatch_channel: str
    environment_id: Optional[str] = None
    environment_name: Optional[str] = None


class RunSummaryResponse(BaseModel):
    """run 列表项。

    列表页只返回排查问题最常用的摘要字段，避免在分页场景里把 payload 全量带回。
    """

    run_id: str
    suite_id: str
    environment_id: Optional[str] = None
    environment_name: Optional[str] = None
    trigger_source: str
    requested_by: str
    status: RunStatus
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class RunDetailResponse(RunSummaryResponse):
    """run 详情。

    详情页会补充 payload 和最近一次状态说明，方便平台排障或给 worker 回传状态时查看。
    """

    payload: dict[str, Any] = Field(default_factory=dict)
    status_message: Optional[str] = Field(None, description="最近一次状态更新的附加说明")


class ListRunsResponse(BaseModel):
    """run 列表响应。"""

    total: int
    limit: int
    offset: int
    items: list[RunSummaryResponse] = Field(default_factory=list)


class UpdateRunStatusRequest(BaseModel):
    """更新 run 状态的最小请求体。

    这个接口给 worker、调度器或运维脚本回写状态时使用，
    API 进程只负责记账，不负责真正执行长任务。
    """

    status: RunStatus
    status_message: Optional[str] = Field(None, description="状态补充说明，例如失败原因")
