# 平台后端说明

这个目录是新测试平台的后端。

如果你第一次接触这里，先记住一句话：

**后端的职责不是执行测试本身，而是“管理并编排执行”。**

这句话非常重要，因为旧系统里最容易混乱的地方，就是把“页面/API 请求”和“长时间执行任务”混在一起。

---

## 1. 新手第一次进入这里，先做什么

建议按这个顺序：

1. 先看 [`docs/new-architecture-quickstart.md`](../../docs/new-architecture-quickstart.md) 把 `.venv` 和依赖装好
2. 回到仓库根目录执行 `make test-backend`
3. 执行 `make backend-dev`
4. 用 `curl` 验证 `/api/v1/health/live`
5. 再开始读这里的代码

如果你跳过前两步，直接读代码，通常很快就会被“为什么导包失败”“服务到底有没有起来”这些问题打断。

---

## 2. 当前阶段的后端边界

第一阶段后端主要负责：

* 管理平台主真源里的平台数据和运行记录
* 接收执行请求
* 创建 run 记录
* 把执行任务投递给 worker
* 查询运行结果和状态
* 给前端提供仪表盘、健康检查、运行记录等接口

第一阶段后端**不负责**：

* 在 HTTP 请求线程里真正执行长时间测试
* 直接承载复杂测试逻辑
* 做重型消息队列系统
* 提供完整持久化数据库实现

也就是说，后端是“管理层”和“编排层”，不是执行器本体。

---

## 3. 先启动，再做最小验证

### 启动命令

在仓库根目录执行：

```bash
source .venv/bin/activate
make backend-dev
```

等价命令是：

```bash
PYTHONPATH=src:platform/backend/src python3 -m uvicorn pyta_platform_backend.main:app --reload
```

优先用 `make backend-dev`，因为它已经帮你带上了正确的 `PYTHONPATH`。

### 第一个验证命令

```bash
curl http://127.0.0.1:8000/api/v1/health/live
```

你应该至少看到：

* `status` 是 `ok`
* `environment` 默认是 `dev`

### 第二个验证命令

```bash
curl http://127.0.0.1:8000/api/v1/dashboard/overview
```

这能帮你确认：

* 路由已经注册
* `DashboardService` 已经挂进应用装配流程

### 第三个验证命令

```bash
curl http://127.0.0.1:8000/api/v1/runs
```

如果第一次是空列表，不是异常，而是因为当前仓库默认使用内存仓库。

### 第四个验证命令

```bash
curl http://127.0.0.1:8000/api/v1/cases
curl http://127.0.0.1:8000/api/v1/suites
curl http://127.0.0.1:8000/api/v1/environments
curl http://127.0.0.1:8000/api/v1/schedules
```

这组接口主要服务平台管理页，当前返回的是：

* 和现代化样例套件对齐的只读目录数据
* 由平台 `run` 主真源补齐的最近活动时间

它们的目的不是先把完整 CRUD 一步做成大而全，而是先把平台管理页接回真实后端资源。

### 第五个验证命令

```bash
curl -X POST http://127.0.0.1:8000/api/v1/environments \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "预发联调环境",
    "base_url": "https://staging.example.com",
    "auth_mode": "Cookie + 单点登录",
    "status": "draft"
  }'
```

这条命令用于验证环境管理的创建链路是否成立：

* 后端能接收结构化环境配置
* 内存仓储能完成写入
* 前端环境页刷新后能看到真实新增项

### 第六个验证命令

```bash
curl http://127.0.0.1:8000/api/v1/environments/<environment_id>

curl -X PATCH http://127.0.0.1:8000/api/v1/environments/<environment_id> \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "预发联调环境-已启用",
    "status": "online"
  }'

curl -X DELETE http://127.0.0.1:8000/api/v1/environments/<environment_id>
```

这组命令用于验证环境资源的完整闭环：

* `GET /environments/{id}` 可返回详情和 variables
* `PATCH /environments/{id}` 使用局部更新，未显式传入的字段会保留
* `DELETE /environments/{id}` 删除成功后，环境目录应不再返回该资源

### 主动创建一条 run

```bash
curl -X POST http://127.0.0.1:8000/api/v1/runs \
  -H 'Content-Type: application/json' \
  -d '{
    "suite_id": "backend-readme-smoke",
    "trigger_source": "manual",
    "requested_by": "newbie",
    "payload": {
      "source": "platform/backend/README.md"
    }
  }'
```

再查一次：

```bash
curl http://127.0.0.1:8000/api/v1/runs
```

这样你能更直观地看到：

* run 记录已经创建
* 当前后端接口闭环至少是通的

---

## 4. 当前目录结构应该怎么读

### `src/pyta_platform_backend/main.py`

这是启动入口。

职责非常薄，只做一件事：

* 调 `create_app()` 得到 `app`

第一次阅读可以把它当成：

**告诉 uvicorn 从哪里把应用拿出来。**

### `src/pyta_platform_backend/app.py`

这是 FastAPI 应用的装配入口，也是后端最值得先看的文件。

主要负责：

* 创建 FastAPI 实例
* 组装默认 service / scheduler / dispatcher / worker runner
* 注册路由
* 把核心对象挂到 `app.state`

对新手来说，可以把这里理解成：

**后端世界的总装车间。**

### `src/pyta_platform_backend/api/`

这里是接口层。

职责应该尽量薄，只做：

* 收请求
* 调 service
* 返回响应

如果你发现这里开始出现一大堆业务逻辑，通常说明分层开始变形了。

### `src/pyta_platform_backend/services/`

这里是业务编排层。

比如 `RunService` 做的事情是：

* 先写 run 记录
* 再投递 dispatcher
* 最后返回接口需要的响应

service 的存在意义，就是避免路由层直接操作 repository、dispatcher、scheduler 等对象。

### `src/pyta_platform_backend/repositories/`

这里是存储访问层。

当前还是内存实现，但后续切到数据库时，理想状态是：

* API 层不用改
* Service 层改动最小
* 只替换 repository 实现

### `src/pyta_platform_backend/workers/`

这里是“投递与执行入口边界”。

第一阶段重点是把这两件事彻底分清：

1. API 进程只创建任务和投递任务
2. 真正执行任务的是 worker 进程

### `src/pyta_platform_backend/scheduler/`

这里负责轻量调度。

当前阶段不引入重型队列系统，所以调度器的责任也保持简单：

* 到点创建 run
* 到点投递任务

而不是在调度器里自己执行测试。

---

## 5. 推荐阅读顺序

如果你想顺着一条线把后端读明白，建议这样看：

1. `src/pyta_platform_backend/main.py`
2. `src/pyta_platform_backend/app.py`
3. `src/pyta_platform_backend/config.py`
4. `src/pyta_platform_backend/api/router.py`
5. `src/pyta_platform_backend/api/routes/health.py`
6. `src/pyta_platform_backend/api/routes/dashboard.py`
7. `src/pyta_platform_backend/api/routes/runs.py`
8. `src/pyta_platform_backend/services/run_service.py`
9. `src/pyta_platform_backend/repositories/run_repository.py`
10. `src/pyta_platform_backend/workers/dispatcher.py`
11. `src/pyta_platform_backend/workers/runner.py`

如果你想先从测试反推代码，可以先看：

* `tests/backend/test_app.py`

这个测试文件已经把当前后端最核心的骨架能力串起来了。

---

## 6. 当前配置从哪里来

后端最小配置放在：

```text
src/pyta_platform_backend/config.py
```

当前比较重要的环境变量有：

* `PLATFORM_BACKEND_APP_ENV`
* `PLATFORM_BACKEND_DEBUG`
* `PLATFORM_BACKEND_API_PREFIX`
* `PLATFORM_BACKEND_RUN_DISPATCH_CHANNEL`
* `PLATFORM_BACKEND_SCHEDULER_POLL_INTERVAL_SECONDS`

如果你只是本地跑起来，默认值已经够用，一般不需要先改。

---

## 7. 为什么包名不是 `platform.backend.*`

这里特意把真正的 Python 包放在：

```text
platform/backend/src/pyta_platform_backend
```

而不是直接做成 `platform.backend.app`。

原因很现实：

Python 标准库里已经有一个 `platform` 模块。
如果你把自己的顶层包也叫 `platform`，后续非常容易出现导入冲突。

所以目录可以叫 `platform/`，但真正的 Python 包名换成 `pyta_platform_backend` 更稳妥。

---

## 8. 当前阶段最容易误判的地方

### 误判 1：`/runs` 能创建记录，就代表已经跑了真实测试

还不能这么理解。

当前阶段里，创建 run 更像是：

* 平台管理链路打通了
* run 可以被创建、投递、更新状态

但它还不等于“真实业务测试已经全部接进引擎”。

### 误判 2：重启服务后 run 消失，说明接口坏了

当前默认仓库实现是内存版，重启后数据清空是预期行为，不是 bug。

### 误判 3：worker 存在，就说明已经是生产级队列

当前 `workers/` 只是把“投递”和“执行”的边界立起来，还不是完整的生产级调度系统。

---

## 9. 后续最优先的演进方向

当前后端已经有骨架，但离“真正好用”还有几步：

1. 对接真实 repository，而不是只用内存存储
2. 和测试引擎打通第一条真实执行闭环
3. 补强 run 详情、状态更新和失败上下文
4. 把 worker 执行入口做得更清晰
5. 给前端提供更稳定的统计和结果接口

只要这几步走通，平台后端就会从“骨架”进入“第一阶段可用”。
