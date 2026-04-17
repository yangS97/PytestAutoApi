"""用于本地测试的 FastAPI 替身。

仓库当前环境还没有安装 fastapi / starlette，
所以这里实现一个足够小的替身，只校验我们的装配逻辑和路由注册逻辑。
"""

import sys
from dataclasses import dataclass
from types import ModuleType, SimpleNamespace
from typing import Callable, List, Optional, Sequence, Set


class HTTPException(Exception):
    """测试替身版 HTTPException。

    测试里不需要完整的框架异常行为，只需要能带出 status_code 和 detail，
    方便断言 service / route 的错误路径。
    """

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _normalize_path(prefix: str, path: str) -> str:
    """把父前缀和子路径拼成统一的 URL。"""

    prefix_part = prefix.strip("/")
    path_part = path.strip("/")
    parts = [part for part in (prefix_part, path_part) if part]
    if not parts:
        return "/"
    return "/" + "/".join(parts)


@dataclass(frozen=True)
class RouteRecord:
    """记录测试里关心的最小路由信息。"""

    path: str
    methods: Set[str]
    endpoint: Callable
    response_model: Optional[object]
    status_code: int
    tags: List[str]


class _RouterBase:
    """APIRouter / FastAPI 共享的最小行为。"""

    def __init__(self, prefix: str = "", tags: Optional[Sequence[str]] = None) -> None:
        self.prefix = prefix
        self.tags = list(tags or [])
        self.routes: List[RouteRecord] = []

    def get(self, path: str, response_model=None, status_code: int = 200):
        return self._build_decorator(
            methods={"GET"},
            path=path,
            response_model=response_model,
            status_code=status_code,
        )

    def post(self, path: str, response_model=None, status_code: int = 200):
        return self._build_decorator(
            methods={"POST"},
            path=path,
            response_model=response_model,
            status_code=status_code,
        )

    def patch(self, path: str, response_model=None, status_code: int = 200):
        return self._build_decorator(
            methods={"PATCH"},
            path=path,
            response_model=response_model,
            status_code=status_code,
        )

    def include_router(self, router: "_RouterBase") -> None:
        """把子路由挂到当前路由树。"""

        for route in router.routes:
            self.routes.append(
                RouteRecord(
                    path=_normalize_path(self.prefix, route.path),
                    methods=set(route.methods),
                    endpoint=route.endpoint,
                    response_model=route.response_model,
                    status_code=route.status_code,
                    tags=list(route.tags),
                )
            )

    def _build_decorator(self, methods, path: str, response_model=None, status_code: int = 200):
        def decorator(func: Callable) -> Callable:
            self.routes.append(
                RouteRecord(
                    path=_normalize_path(self.prefix, path),
                    methods=set(methods),
                    endpoint=func,
                    response_model=response_model,
                    status_code=status_code,
                    tags=list(self.tags),
                )
            )
            return func

        return decorator


class APIRouter(_RouterBase):
    """测试替身版 APIRouter。"""


class FastAPI(_RouterBase):
    """测试替身版 FastAPI。"""

    def __init__(self, title: str, debug: bool = False, version: str = "0.1.0") -> None:
        super().__init__(prefix="")
        self.title = title
        self.debug = debug
        self.version = version
        self.state = SimpleNamespace()


def install_fake_fastapi(monkeypatch) -> ModuleType:
    """把 fake fastapi 注入到 sys.modules。"""

    fake_module = ModuleType("fastapi")
    fake_module.FastAPI = FastAPI
    fake_module.APIRouter = APIRouter
    fake_module.HTTPException = HTTPException
    fake_module.status = SimpleNamespace(
        HTTP_200_OK=200,
        HTTP_202_ACCEPTED=202,
        HTTP_404_NOT_FOUND=404,
    )
    monkeypatch.setitem(sys.modules, "fastapi", fake_module)
    return fake_module
