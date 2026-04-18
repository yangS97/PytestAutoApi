"""平台管理面 schema。

第一阶段先给管理页提供最小可用的数据契约：
- cases: 用例目录摘要
- suites: 套件目录摘要
- environments: 环境目录摘要
- schedules: 调度目录摘要

这些接口当前主要服务页面展示和 environment 的首个完整资源闭环，
暂不承担完整的复杂编辑能力。
"""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class CaseSummaryResponse(BaseModel):
    """用例列表项。"""

    id: str
    name: str
    module: str
    method: str
    priority: str
    status: str


class SuiteSummaryResponse(BaseModel):
    """套件列表项。"""

    id: str
    name: str
    case_count: int
    last_run: str = Field(..., description="最近一次 run 的展示时间；没有记录时返回提示文案")
    schedule: str


class EnvironmentSummaryResponse(BaseModel):
    """环境列表项。"""

    id: str
    name: str
    base_url: str
    auth_mode: str
    status: str


class EnvironmentDetailResponse(EnvironmentSummaryResponse):
    """环境详情。

    当前先把 `variables` 透传出来，后续前端真正接变量编辑器时，
    就不需要再重新发明一套详情结构。
    """

    variables: Dict[str, object] = Field(default_factory=dict)


class CreateEnvironmentRequest(BaseModel):
    """创建环境的最小请求体。"""

    name: str = Field(..., description="环境名称")
    base_url: str = Field(..., description="环境基础地址")
    auth_mode: str = Field(..., description="鉴权模式说明")
    status: str = Field("draft", description="环境状态：online / draft")
    variables: Dict[str, object] = Field(default_factory=dict, description="预留：环境变量")


class CreateEnvironmentResponse(EnvironmentDetailResponse):
    """创建环境后的确认信息。"""


class UpdateEnvironmentRequest(BaseModel):
    """更新环境的 patch 请求体。"""

    name: Optional[str] = Field(None, description="环境名称")
    base_url: Optional[str] = Field(None, description="环境基础地址")
    auth_mode: Optional[str] = Field(None, description="鉴权模式说明")
    status: Optional[str] = Field(None, description="环境状态：online / draft")
    variables: Optional[Dict[str, object]] = Field(None, description="可选：环境变量")


class UpdateEnvironmentResponse(EnvironmentDetailResponse):
    """更新环境后的响应。"""


class DeleteEnvironmentResponse(EnvironmentSummaryResponse):
    """删除环境后的确认响应。"""


class ScheduleSummaryResponse(BaseModel):
    """调度列表项。"""

    id: str
    name: str
    cron: str
    target: str
    environment_id: Optional[str] = None
    environment_name: Optional[str] = None
    last_run: str = Field(..., description="最近一次与目标套件相关的 run 时间")
    status: str
