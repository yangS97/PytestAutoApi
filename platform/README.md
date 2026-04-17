# platform 目录说明

这个目录专门存放“测试平台”相关代码。

如果你第一次进入这个仓库，先记住一句话：

* `src/testflow_engine/` 负责“怎么执行测试”
* `platform/` 负责“怎么管理、触发、查看测试”

也就是说，`platform/` 不是测试逻辑本身，而是对测试资产和执行过程的管理层。

---

## 1. 第一次上手先看哪里

如果你现在的目标是“把新架构先跑起来”，建议按这个顺序阅读：

1. [`docs/new-architecture-quickstart.md`](../docs/new-architecture-quickstart.md)
2. 本文
3. [`platform/backend/README.md`](./backend/README.md)
4. [`platform/frontend/README.md`](./frontend/README.md)
5. [`src/testflow_engine/README.md`](../src/testflow_engine/README.md)

不要一开始就被旧框架目录带走。

旧框架主要在：

* `data/`
* `test_case/`
* `utils/`
* `run.py`

这些目录主要服务迁移和兼容，不是新同学第一天最该看的内容。

---

## 2. `platform/` 到底解决什么问题

平台层要解决的是这些日常问题：

* 测试用例在哪里维护
* 套件怎么组织和触发
* 环境和鉴权信息怎么管理
* 调度任务怎么查看
* 运行结果怎么回看和排障

所以平台关心的是“管理”和“使用效率”，而不是把具体 HTTP 断言逻辑写死在页面或接口里。

---

## 3. 目录怎么理解

### `platform/backend/`

后端管理服务，负责：

* 提供 FastAPI 接口
* 管理 run、仪表盘、健康检查等平台能力
* 创建执行任务
* 把长时间测试投递给 worker，而不是堵塞 HTTP 请求线程

第一次阅读时，优先关注这些点：

* 路由怎么注册
* run 怎么创建
* 为什么 worker 不在路由里直接跑长任务
* 为什么当前数据重启会丢失

### `platform/frontend/`

前端管理界面，负责：

* 平台导航和页面壳层
* 仪表盘
* 运行记录
* 用例 / 套件 / 环境 / 调度等管理页面骨架
* 前端对真实 API 和 mock 的兼容切换

第一次阅读时，优先关注这些点：

* 页面和路由怎么组织
* API 请求入口怎么收口
* 为什么保留 mock 兜底
* 本地开发时为什么需要配置 `.env.local`

---

## 4. 为什么平台被当作主真源

当前团队规模很小，通常只有 1 人，最多 2-3 人。

这种情况下，如果日常维护测试资产还必须频繁改仓库文件、提交 Git、再本地跑脚本，效率提升会被严重抵消。

所以第一阶段选择：

* 平台作为主真源
* 平台覆盖 80% 常规接口场景
* 复杂逻辑继续通过代码插件扩展

这样做的好处是：

* 常规场景能明显提效
* 复杂场景不被强行低代码化
* 平台不会过早膨胀成一个臃肿系统

---

## 5. 平台和引擎怎么配合

最简单的理解方式是：

```text
平台负责“管”
引擎负责“跑”
```

拆开看就是：

* 平台后端决定创建什么 run、记录什么状态、什么时候调度
* worker 拿到任务后调用执行引擎
* 引擎负责真正的请求发送、断言、报告收集
* 前端负责把这些状态和结果展示给人看

所以如果你在某个页面里看到大量测试执行细节，或者在引擎里看到大量页面/数据库语义，通常说明边界开始混乱了。

---

## 6. 新手第一天建议完成的最小闭环

建议按下面这条链路自测一次：

1. 在仓库根目录创建 `.venv` 并执行 `make install-dev`
2. 执行 `make test-new`
3. 执行 `make backend-dev`
4. 用 `curl http://127.0.0.1:8000/api/v1/health/live` 验证后端启动
5. 在 `platform/frontend/.env.local` 中把 `VITE_API_BASE_URL` 指向 `http://127.0.0.1:8000/api/v1`
6. 执行 `npm run dev`
7. 打开 `/dashboard` 和 `/runs` 页面验证前后端联通

更具体的命令写在 [`docs/new-architecture-quickstart.md`](../docs/new-architecture-quickstart.md) 里。
