"""worker 本地控制相关 schema。"""

from typing import Optional

from pydantic import BaseModel, Field

from pyta_platform_backend.schemas.run import RunDetailResponse


class RunNextResponse(BaseModel):
    """本地 worker 消费结果。

    这个响应只服务开发阶段和手动验证，不是最终的生产级 worker API。
    """

    consumed: bool = Field(..., description="本次是否真的消费到一条任务")
    detail: Optional[RunDetailResponse] = Field(None, description="消费后的 run 详情")

