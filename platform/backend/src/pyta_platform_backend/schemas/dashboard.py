"""仪表盘相关 schema。

第一阶段的 dashboard 不追求“全量平台分析能力”，而是先服务两个高频场景：
1. 让测试同学一进平台就能看到当前整体健康度。
2. 让前端首页能尽快摆脱纯 mock，接上真实后端数据。
"""

from pydantic import BaseModel, Field


class DashboardMetricResponse(BaseModel):
    """首页顶部指标卡的数据结构。"""

    key: str
    label: str
    value: str
    description: str
    trend: str


class DashboardFocusItemResponse(BaseModel):
    """首页重点事项卡片。"""

    id: str
    title: str
    owner: str
    status: str
    summary: str


class DashboardRecentRunResponse(BaseModel):
    """首页最近运行摘要。

    这里返回的是“首页可直接展示”的轻量字段，而不是完整 run 详情。
    """

    id: str
    name: str
    target: str
    status: str
    started_at: str
    duration: str
    starter: str
    raw_status: str = Field(
        ...,
        description="原始 run 状态，便于前端需要时做更细粒度映射",
    )


class DashboardOverviewResponse(BaseModel):
    """首页总览响应。"""

    metrics: list[DashboardMetricResponse] = Field(default_factory=list)
    focus_items: list[DashboardFocusItemResponse] = Field(default_factory=list)
    recent_runs: list[DashboardRecentRunResponse] = Field(default_factory=list)
