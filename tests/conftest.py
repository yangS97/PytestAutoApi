"""新架构测试的公共路径准备。

这里故意把“新引擎 src 路径”和“后端 src 路径”都显式加到 ``sys.path``。
原因是当前仓库正处在重构过渡期：

1. 旧框架仍然保留在根目录结构中。
2. 新引擎采用标准 ``src/`` 布局。
3. 新后端为了避免与标准库 ``platform`` 冲突，把真正的 Python 包放在
   ``platform/backend/src/pyta_platform_backend``。

在这种过渡阶段，测试如果不先把路径准备好，就很容易出现：
“代码已经写了，但 pytest 找不到包”的假失败。
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENGINE_SRC = REPO_ROOT / "src"
BACKEND_SRC = REPO_ROOT / "platform" / "backend" / "src"


def _ensure_python_path(path: Path) -> None:
    """把目录安全地加入 Python 搜索路径。

    这个辅助函数做的事情很简单，但专门封装出来是为了让新手读代码时更容易理解：
    - 为什么要加路径
    - 加的是哪个路径
    - 如何避免重复插入
    """

    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)


_ensure_python_path(ENGINE_SRC)
_ensure_python_path(BACKEND_SRC)
