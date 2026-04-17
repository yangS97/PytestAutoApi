"""应用启动入口。

真实部署时可以使用：
``uvicorn pyta_platform_backend.main:app --reload``

本仓库当前没有补充根级依赖声明，所以这里只提供入口文件，不改共享配置。
"""

from pyta_platform_backend.app import create_app

app = create_app()
