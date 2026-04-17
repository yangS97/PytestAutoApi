"""健康检查响应模型。"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """健康检查响应。

    这个模型刻意保持简单，方便未来把 live/readiness 拆开时保持接口稳定。
    """

    status: str
    service: str
    environment: str
