"""平台后端骨架的公共导出。

这里故意把真正的 Python 包放在 ``platform/backend/src/pyta_platform_backend`` 下，
而不是直接做成顶层 ``platform`` 包，避免和 Python 标准库 ``platform`` 同名冲突。
"""

from pyta_platform_backend.app import create_app
from pyta_platform_backend.config import BackendSettings

__all__ = ["BackendSettings", "create_app"]
