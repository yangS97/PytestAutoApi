# 这个 Makefile 的目标不是“花哨”，而是给团队一个稳定、统一、易记的入口。
# 对新手来说，可以把它理解成“常用命令菜单”：
# 以后不需要记住很长的命令，只需要执行 `make 目标名` 即可。

.PHONY: help install-dev test-engine test-backend test-new backend-dev frontend-dev frontend-build

help:
	@echo "可用命令："
	@echo "  make install-dev   安装新架构开发依赖"
	@echo "  make test-engine   运行新测试引擎相关测试"
	@echo "  make test-backend  运行新平台后端相关测试"
	@echo "  make test-new      运行新架构全部结构性测试"
	@echo "  make backend-dev   启动 FastAPI 开发服务"
	@echo "  make frontend-dev  启动 Vue 前端开发服务"
	@echo "  make frontend-build 构建 Vue 前端产物"

install-dev:
	python3 -m pip install -e ".[dev]"

test-engine:
	python3 -m pytest tests/engine tests/compat

test-backend:
	python3 -m pytest tests/backend

test-new:
	python3 -m pytest tests/engine tests/compat tests/backend

backend-dev:
	PYTHONPATH=src:platform/backend/src python3 -m uvicorn pyta_platform_backend.main:app --reload

frontend-dev:
	cd platform/frontend && npm run dev

frontend-build:
	cd platform/frontend && npm run build -- --mode production
