"""后端骨架测试的公共准备。"""

import sys
from pathlib import Path

BACKEND_SRC = Path(__file__).resolve().parents[2] / "platform" / "backend" / "src"

# 测试只把后端 src 目录加入搜索路径，不把顶层 platform 做成 Python 包，
# 这样可以避免与标准库 platform 冲突。
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))
