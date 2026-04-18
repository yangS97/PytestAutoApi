"""平台管理面仓储。

当前阶段数据库还未接入，所以先用内存仓储承接：
- 用例目录
- 套件目录
- 环境目录
- 调度目录

这样页面即便还处于骨架期，也不需要继续长期依赖前端 mock。
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from uuid import uuid4

import yaml


@dataclass(frozen=True)
class CaseRecord:
    """用例目录记录。"""

    id: str
    name: str
    module: str
    method: str
    priority: str
    status: str


@dataclass(frozen=True)
class SuiteRecord:
    """套件目录记录。"""

    id: str
    name: str
    case_count: int
    schedule: str


@dataclass(frozen=True)
class EnvironmentRecord:
    """环境目录记录。"""

    id: str
    name: str
    base_url: str
    auth_mode: str
    status: str
    variables: dict[str, object]


@dataclass(frozen=True)
class ScheduleRecord:
    """调度目录记录。"""

    id: str
    name: str
    cron: str
    target_suite_id: str
    environment_id: str
    status: str


class InMemoryManagementRepository:
    """平台管理页的内存仓储。

    这里的目录数据故意与当前已落地的现代化演示资产保持一致：
    - cases / suites 对齐 demo suite 的标准化案例
    - environments / schedules 提供平台 MVP 所需的最小目录

    等平台数据库接入后，路由和服务层不需要跟着一起改。
    """

    def __init__(self) -> None:
        default_host = self._load_default_host()
        self._cases = self._build_cases()
        self._suites = self._build_suites()
        self._environments = {
            item.id: item for item in self._build_environments(default_host)
        }
        self._schedules = self._build_schedules()

    def list_cases(self) -> list[CaseRecord]:
        """列出当前可展示的用例目录。"""

        return list(self._cases)

    def list_suites(self) -> list[SuiteRecord]:
        """列出当前可展示的套件目录。"""

        return list(self._suites)

    def list_environments(self) -> list[EnvironmentRecord]:
        """列出环境目录。"""

        return list(self._environments.values())

    def get_environment_by_id(self, environment_id: str) -> Optional[EnvironmentRecord]:
        """按 id 读取环境。"""

        return self._environments.get(environment_id)

    def create_environment(
        self,
        *,
        name: str,
        base_url: str,
        auth_mode: str,
        status: str,
        variables: dict[str, object],
    ) -> Optional[EnvironmentRecord]:
        """创建新的环境目录记录。"""

        normalized_name = name.strip().lower()
        if any(
            item.name.strip().lower() == normalized_name
            for item in self._environments.values()
        ):
            raise ValueError(f"环境名称已存在: {name}")

        record = EnvironmentRecord(
            id=uuid4().hex,
            name=name,
            base_url=base_url,
            auth_mode=auth_mode,
            status=status,
            variables=dict(variables),
        )
        self._environments[record.id] = record
        return record

    def update_environment(
        self,
        environment_id: str,
        *,
        name: str,
        base_url: str,
        auth_mode: str,
        status: str,
        variables: dict[str, object],
    ) -> Optional[EnvironmentRecord]:
        """更新环境目录记录。"""

        existing = self.get_environment_by_id(environment_id)
        if existing is None:
            return None

        normalized_name = name.strip().lower()
        if any(
            item.id != environment_id and item.name.strip().lower() == normalized_name
            for item in self._environments.values()
        ):
            raise ValueError(f"环境名称已存在: {name}")

        updated = EnvironmentRecord(
            id=existing.id,
            name=name,
            base_url=base_url,
            auth_mode=auth_mode,
            status=status,
            variables=dict(variables),
        )
        self._environments[environment_id] = updated
        return updated

    def delete_environment(self, environment_id: str) -> Optional[EnvironmentRecord]:
        """删除环境目录记录。"""

        return self._environments.pop(environment_id, None)

    def list_schedules(self) -> list[ScheduleRecord]:
        """列出调度目录。"""

        return list(self._schedules)

    @staticmethod
    def _build_cases() -> list[CaseRecord]:
        """构造和 demo suite 对齐的用例目录。"""

        return [
            CaseRecord(
                id="login_success",
                name="正常登录",
                module="鉴权",
                method="POST",
                priority="P0",
                status="active",
            ),
            CaseRecord(
                id="login_wrong_password",
                name="密码错误",
                module="鉴权",
                method="POST",
                priority="P1",
                status="active",
            ),
            CaseRecord(
                id="login_empty_password",
                name="密码为空",
                module="鉴权",
                method="POST",
                priority="P1",
                status="active",
            ),
            CaseRecord(
                id="persona_person_page",
                name="查询人设分页列表",
                module="培训对练",
                method="GET",
                priority="P1",
                status="active",
            ),
            CaseRecord(
                id="persona_evaluate_page",
                name="获取可选评估包列表",
                module="培训对练",
                method="POST",
                priority="P1",
                status="active",
            ),
            CaseRecord(
                id="persona_chapter_list",
                name="预览评估包章节详情",
                module="培训对练",
                method="GET",
                priority="P2",
                status="active",
            ),
            CaseRecord(
                id="persona_bind_package",
                name="给指定人设绑定评估包",
                module="培训对练",
                method="POST",
                priority="P0",
                status="active",
            ),
            CaseRecord(
                id="persona_verify_refresh",
                name="验证绑定后人设列表刷新",
                module="培训对练",
                method="GET",
                priority="P1",
                status="active",
            ),
            CaseRecord(
                id="persona_filter_type",
                name="按类型筛选人设",
                module="培训对练",
                method="GET",
                priority="P2",
                status="draft",
            ),
        ]

    @staticmethod
    def _build_suites() -> list[SuiteRecord]:
        """构造与当前样例套件一致的套件目录。"""

        return [
            SuiteRecord(
                id="demo-login-auth",
                name="登录鉴权",
                case_count=3,
                schedule="工作日 09:00",
            ),
            SuiteRecord(
                id="demo-persona-library",
                name="培训对练 - 人设库管理",
                case_count=6,
                schedule="每天 22:00",
            ),
        ]

    @staticmethod
    def _build_environments(default_host: str) -> list[EnvironmentRecord]:
        """构造当前平台环境目录。"""

        return [
            EnvironmentRecord(
                id="env-default-live",
                name="默认联调环境",
                base_url=default_host,
                auth_mode="账号密码登录 + Token 注入",
                status="online",
                variables={},
            ),
            EnvironmentRecord(
                id="env-demo-mock",
                name="离线演示环境",
                base_url="https://mock.platform.local",
                auth_mode="Mock Token / 本地演示",
                status="draft",
                variables={},
            ),
        ]

    @staticmethod
    def _build_schedules() -> list[ScheduleRecord]:
        """构造当前平台调度目录。"""

        return [
            ScheduleRecord(
                id="schedule-login-smoke",
                name="工作日登录鉴权冒烟",
                cron="0 9 * * 1-5",
                target_suite_id="demo-login-auth",
                environment_id="env-default-live",
                status="active",
            ),
            ScheduleRecord(
                id="schedule-persona-nightly",
                name="夜间人设库回归",
                cron="0 22 * * *",
                target_suite_id="demo-persona-library",
                environment_id="env-demo-mock",
                status="paused",
            ),
        ]

    @staticmethod
    def _load_default_host() -> str:
        """从旧配置里读取默认 host，方便新旧平台目录看到同一基线。"""

        root = Path(__file__).resolve().parents[5]
        config_path = root / "common" / "config.yaml"
        if not config_path.exists():
            return "https://api-test.yanjiai.com"

        with config_path.open("r", encoding="utf-8") as file:
            payload = yaml.safe_load(file) or {}
        return str(payload.get("host") or "https://api-test.yanjiai.com").rstrip("/")
