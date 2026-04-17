"""登录鉴权 bootstrap 插件。

这个插件的定位很明确：
它不是把旧框架里所有隐式鉴权行为原封不动搬过来，
而是为新框架提供一种清晰、可配置、可测试的鉴权 bootstrap 机制。

第一阶段它解决的核心问题是：

* 某些业务套件本身不包含登录 case
* 但执行这些 case 之前，必须先拿到一个 token
* 并且后续请求需要统一带上这个 token
"""

from typing import Any, Dict, Optional

from .._field_path import resolve_field_path
from ..models import ExecutionContext, TestCaseDefinition, TestRunDefinition
from .base import EnginePlugin


class BootstrapAuthPlugin(EnginePlugin):
    """最小可用的登录鉴权插件。"""

    name = "bootstrap-auth-plugin"

    def __init__(self, http_client=None) -> None:
        self._http_client = http_client

    def before_run(self, run: TestRunDefinition, context: ExecutionContext) -> None:
        """在 run 开始前尝试做一次登录 bootstrap。"""

        config = self._get_auth_config(context)
        if not config:
            return

        cache_bucket = context.variables.setdefault("cache", {})
        token_key = str(config.get("token_cache_key") or "auth_token")
        if cache_bucket.get(token_key):
            return

        login_url = str(config.get("login_url") or "").strip()
        if not login_url:
            raise ValueError("auth_bootstrap 缺少 login_url")

        body = dict(config.get("body") or {})
        headers = dict(config.get("headers") or {})
        request_mode = str(config.get("request_mode") or "json").lower()

        client = self._ensure_client()
        try:
            if request_mode == "form":
                response = client.post(login_url, data=body, headers=headers)
            else:
                response = client.post(login_url, json=body, headers=headers)
        finally:
            self._close_client_if_needed()

        payload = response.json()
        token_path = str(config.get("token_path") or "data.token")
        token = resolve_field_path(payload, token_path)
        if not token:
            raise ValueError("登录成功后未能从响应中提取 token: %s" % token_path)

        cache_bucket[token_key] = token

    def before_case(self, case: TestCaseDefinition, context: ExecutionContext) -> None:
        """在每个 case 发送前把 token 注入 header。"""

        config = self._get_auth_config(context)
        if not config:
            return

        cache_bucket = context.variables.setdefault("cache", {})
        token_key = str(config.get("token_cache_key") or "auth_token")
        token = cache_bucket.get(token_key)
        if not token:
            return

        header_name = str(config.get("header_name") or "Authorization")
        header_template = str(config.get("header_template") or "{token}")

        headers = dict(case.request.headers or {})
        if header_name not in headers:
            headers[header_name] = header_template.format(token=token)
            case.request.headers = headers

    @staticmethod
    def _get_auth_config(context: ExecutionContext) -> Optional[Dict[str, Any]]:
        """从运行时变量里取 auth bootstrap 配置。"""

        raw = context.variables.get("auth_bootstrap")
        return dict(raw) if isinstance(raw, dict) else None

    def _ensure_client(self):
        """惰性创建 httpx client。"""

        if self._http_client is not None:
            self._owns_client = False
            return self._http_client

        import httpx

        self._owns_client = True
        self._http_client = httpx.Client()
        return self._http_client

    def _close_client_if_needed(self) -> None:
        """关闭插件自己创建的 client。"""

        if getattr(self, "_owns_client", False) and self._http_client is not None:
            self._http_client.close()
            self._http_client = None

