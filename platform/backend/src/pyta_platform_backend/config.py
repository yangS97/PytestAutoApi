"""平台后端配置定义。"""

import os
from pathlib import Path

from pydantic import BaseModel


class BackendSettings(BaseModel):
    """后端服务的最小配置集合。

    第一阶段只保留骨架真正需要的字段：
    1. FastAPI 应用标题、版本和 API 前缀
    2. worker 投递通道标识
    3. 轻量 scheduler 的轮询周期
    """

    app_name: str = "PytestAutoApi Platform Backend"
    app_version: str = "0.1.0"
    app_env: str = "dev"
    debug: bool = False
    api_prefix: str = "/api/v1"
    run_dispatch_channel: str = "memory-worker"
    scheduler_poll_interval_seconds: int = 30
    state_db_path: str = ""

    @classmethod
    def _field_default(cls, field_name: str):
        """读取字段默认值，兼容 Pydantic v1/v2。

        review 已经指出当前仓库环境可能同时出现 v1 和 v2，
        所以这里不再把默认值读取逻辑写死在某一版实现上。
        """

        if hasattr(cls, "model_fields"):
            return cls.model_fields[field_name].default
        return cls.__fields__[field_name].default

    @classmethod
    def from_env(cls) -> "BackendSettings":
        """从环境变量构造配置。

        这里先不用更重的 settings 框架，避免在骨架阶段引入额外依赖。
        等平台需要更复杂的配置来源时，再替换成专门的配置模块即可。
        """

        raw_values: dict[str, object] = {
            "app_name": os.getenv(
                "PLATFORM_BACKEND_APP_NAME",
                cls._field_default("app_name"),
            ),
            "app_version": os.getenv(
                "PLATFORM_BACKEND_APP_VERSION",
                cls._field_default("app_version"),
            ),
            "app_env": os.getenv("PLATFORM_BACKEND_APP_ENV", cls._field_default("app_env")),
            "debug": cls._read_bool(
                os.getenv("PLATFORM_BACKEND_DEBUG"),
                default=cls._field_default("debug"),
            ),
            "api_prefix": os.getenv(
                "PLATFORM_BACKEND_API_PREFIX",
                cls._field_default("api_prefix"),
            ),
            "run_dispatch_channel": os.getenv(
                "PLATFORM_BACKEND_RUN_DISPATCH_CHANNEL",
                cls._field_default("run_dispatch_channel"),
            ),
            "scheduler_poll_interval_seconds": int(
                os.getenv(
                    "PLATFORM_BACKEND_SCHEDULER_POLL_INTERVAL_SECONDS",
                    cls._field_default("scheduler_poll_interval_seconds"),
                )
            ),
            "state_db_path": os.getenv(
                "PLATFORM_BACKEND_STATE_DB_PATH",
                cls._field_default("state_db_path"),
            ),
        }
        return cls(**raw_values)

    @staticmethod
    def _read_bool(raw_value: str, default: bool) -> bool:
        """把环境变量里的字符串转成布尔值。"""

        if raw_value is None:
            return default
        return raw_value.strip().lower() in {"1", "true", "yes", "on"}

    def resolve_state_db_path(self) -> str:
        """解析平台状态库路径。

        规则保持很克制：
        - 显式传了 `state_db_path` 就直接使用
        - test 环境默认走 sqlite 内存库，避免测试相互污染
        - 其他环境默认落到仓库内 `.runtime/platform-state.sqlite3`
        """

        if self.state_db_path:
            return self.state_db_path

        if self.app_env == "test":
            return ":memory:"

        root = Path(__file__).resolve().parents[4]
        return str(root / ".runtime" / "platform-state.sqlite3")
