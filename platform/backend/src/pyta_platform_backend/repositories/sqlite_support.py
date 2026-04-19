"""sqlite 轻量持久化公共工具。

这一层刻意保持非常薄：
- 单人工作台优先
- 不引入 ORM / migration 体系
- 只负责 sqlite 连接、JSON 与时间序列化这些公共细节
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


def connect_sqlite(database_path: str) -> sqlite3.Connection:
    """创建 sqlite 连接，并在文件模式下确保父目录存在。"""

    if database_path != ":memory:":
        Path(database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path, timeout=5, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def dump_json(value: Any) -> str:
    """把 Python 对象序列化为 JSON 文本。"""

    return json.dumps(value, ensure_ascii=False)


def load_json(value: Optional[str], default: Any) -> Any:
    """把 JSON 文本还原为 Python 对象。"""

    if not value:
        return default
    return json.loads(value)


def dump_datetime(value: Optional[datetime]) -> Optional[str]:
    """把 datetime 序列化成 ISO 文本。"""

    if value is None:
        return None
    return value.isoformat()


def load_datetime(value: Optional[str]) -> Optional[datetime]:
    """把 ISO 文本还原为 datetime。"""

    if not value:
        return None
    return datetime.fromisoformat(value)
