"""
字段路径读取工具。

当前新引擎里，至少有两层会读取 `a.b.c` 这样的简单路径：
1. 断言层需要从响应 / context 中取值。
2. 变量渲染层需要从 `context.variables` 中取模板变量。

把这段逻辑集中到一个地方，能避免“断言能取到、模板却取不到”这种边界漂移。
"""

from typing import Any


_MISSING = object()


def resolve_field_path(source: Any, selector: str, default: Any = None) -> Any:
    """按点路径读取值，找不到时返回 default。"""

    if not selector:
        return source

    current = source
    for part in selector.split("."):
        if part == "":
            continue
        if isinstance(current, dict):
            if part not in current:
                return default
            current = current[part]
            continue
        if isinstance(current, list) and part.isdigit():
            index = int(part)
            if index >= len(current):
                return default
            current = current[index]
            continue
        return default
    return current


def has_field_path(source: Any, selector: str) -> bool:
    """判断路径是否存在，用于模板层区分“值是 None”和“变量没定义”。"""

    return resolve_field_path(source=source, selector=selector, default=_MISSING) is not _MISSING
