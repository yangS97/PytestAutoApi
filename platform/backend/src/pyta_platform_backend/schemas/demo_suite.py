"""演示/迁移样例套件相关 schema。"""

from typing import List, Optional

from pydantic import BaseModel, Field

from pyta_platform_backend.schemas.run import CreateRunResponse


class DemoSuiteSummaryResponse(BaseModel):
    """样例套件摘要。

    这些套件不是最终平台真源的数据模型，而是当前重构阶段用来验证：
    “旧测试语义是否已经被新框架正确承接”的桥接资产。
    """

    suite_id: str
    title: str
    description: str
    source: str
    case_count: int
    supports_live_http: bool = True


class ListDemoSuitesResponse(BaseModel):
    """样例套件列表响应。"""

    items: List[DemoSuiteSummaryResponse] = Field(default_factory=list)


class CreateDemoSuiteRunRequest(BaseModel):
    """从样例套件创建运行任务。

    mode:
    - `live`：走真实 HTTP
    - `mock`：走内置 mock 响应
    """

    mode: str = Field("live", description="运行模式：live / mock")
    requested_by: str = Field("platform-user", description="发起人")
    host_override: Optional[str] = Field(None, description="可选：覆盖默认 host")


class CreateDemoSuiteRunResponse(CreateRunResponse):
    """样例套件创建运行后的确认信息。"""

    suite_id: str
    mode: str

