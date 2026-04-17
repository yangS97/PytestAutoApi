import { apiClient, isApiError } from '@/api/client';
import { extractRunCollection, normalizeRunSummary } from '@/api/adapters/runs';
import { managementApi } from '@/api/modules/management';
import type {
  ApiResolvedData,
  DashboardMetric,
  DashboardOverview,
  FocusItem,
  RunSummary,
} from '@/types/platform';

type UnknownRecord = Record<string, unknown>;

const forceMock = import.meta.env.VITE_USE_MOCK === 'true';

const wait = (ms = 120) => new Promise((resolve) => window.setTimeout(resolve, ms));

const mockOverview: DashboardOverview = {
  metrics: [
    {
      key: 'cases',
      label: '可维护用例',
      value: '128',
      description: '平台主真源中已结构化维护的 HTTP 用例数量',
      trend: '+12 本周',
    },
    {
      key: 'suites',
      label: '活跃套件',
      value: '14',
      description: '用于冒烟、回归和联调的常用套件集合',
      trend: '3 个待补前置依赖',
    },
    {
      key: 'runs',
      label: '今日执行',
      value: '36',
      description: '人工触发与调度触发合并后的运行次数',
      trend: '失败 4 次',
    },
    {
      key: 'schedules',
      label: '已启用调度',
      value: '6',
      description: '当前仍在生产中持续跑的计划任务',
      trend: '2 个任务待迁移',
    },
  ],
  focusItems: [
    {
      id: 'focus-1',
      title: '登录链路迁移到平台主真源',
      owner: '测试平台',
      status: 'attention',
      summary: '优先把鉴权、变量提取、断言抽成可编辑结构，减少 YAML 复制。',
    },
    {
      id: 'focus-2',
      title: '回归套件拆分为冒烟 / 完整 / 夜跑',
      owner: '回归测试',
      status: 'planned',
      summary: '先明确套件层级和依赖顺序，后续调度中心才方便落地。',
    },
    {
      id: 'focus-3',
      title: '运行结果视图保留失败上下文',
      owner: '执行中心',
      status: 'stable',
      summary: '结果页要同时承载日志、响应片段和问题定位入口。',
    },
  ],
  recentRuns: [
    {
      id: 'run-101',
      name: '登录冒烟',
      target: 'suite/login-smoke',
      status: 'success',
      startedAt: '今天 09:20',
      duration: '2m 18s',
      starter: 'scheduler',
      rawStatus: 'succeeded',
    },
    {
      id: 'run-102',
      name: '订单回归',
      target: 'suite/order-regression',
      status: 'failed',
      startedAt: '今天 10:05',
      duration: '8m 40s',
      starter: '李明',
      rawStatus: 'failed',
    },
    {
      id: 'run-103',
      name: '用户中心单用例重放',
      target: 'case/user-profile-update',
      status: 'running',
      startedAt: '今天 10:31',
      duration: '执行中',
      starter: '王芳',
      rawStatus: 'running',
    },
  ],
};

const isRecord = (value: unknown): value is UnknownRecord =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const readString = (value: unknown) => (typeof value === 'string' ? value : '');

const shouldFallbackToNextLayer = (error: unknown) => {
  if (error instanceof TypeError) {
    return true;
  }

  if (!isApiError(error)) {
    return false;
  }

  return [404, 405, 501, 502, 503, 504].includes(error.status);
};

const normalizeMetric = (payload: unknown, index: number): DashboardMetric | null => {
  if (!isRecord(payload)) {
    return null;
  }

  const label = readString(payload.label) || readString(payload.title);
  const value = payload.value ?? payload.count ?? payload.total;

  if (!label || value === undefined || value === null) {
    return null;
  }

  return {
    key: readString(payload.key) || `metric-${index}`,
    label,
    value: String(value),
    description: readString(payload.description) || '来自后端接口的统计摘要',
    trend: readString(payload.trend) || readString(payload.subtitle) || '已接入真实接口',
  };
};

const normalizeFocusItem = (payload: unknown, index: number): FocusItem | null => {
  if (!isRecord(payload)) {
    return null;
  }

  const status = readString(payload.status);
  const normalizedStatus: FocusItem['status'] =
    status === 'stable' || status === 'attention' || status === 'planned' ? status : 'planned';

  const title = readString(payload.title) || readString(payload.name);

  if (!title) {
    return null;
  }

  return {
    id: readString(payload.id) || `focus-${index}`,
    title,
    owner: readString(payload.owner) || '平台后端',
    status: normalizedStatus,
    summary: readString(payload.summary) || readString(payload.description) || '暂无补充说明',
  };
};

const normalizeDashboardOverview = (payload: unknown): DashboardOverview | null => {
  const root = isRecord(payload) && isRecord(payload.data) ? payload.data : payload;

  if (!isRecord(root)) {
    return null;
  }

  const metrics = (Array.isArray(root.metrics) ? root.metrics : [])
    .map(normalizeMetric)
    .filter((item): item is DashboardMetric => item !== null);
  const focusItems = (
    Array.isArray(root.focusItems)
      ? root.focusItems
      : Array.isArray(root.focus_items)
        ? root.focus_items
        : []
  )
    .map(normalizeFocusItem)
    .filter((item): item is FocusItem => item !== null);
  const recentRuns = extractRunCollection(root.recentRuns ?? root.recent_runs)
    .map((item, index) => normalizeRunSummary(item, index));

  if (!metrics.length && !focusItems.length && !recentRuns.length) {
    return null;
  }

  return {
    metrics,
    focusItems,
    recentRuns,
  };
};

const buildCompatibilityOverview = (runs: RunSummary[], healthPayload?: unknown): DashboardOverview => {
  const successCount = runs.filter((item) => item.status === 'success').length;
  const failedCount = runs.filter((item) => item.status === 'failed' || item.status === 'warning').length;
  const inflightCount = runs.filter((item) => item.status === 'queued' || item.status === 'running').length;
  const health = isRecord(healthPayload) ? healthPayload : {};
  const environment = readString(health.environment) || 'unknown';
  const service = readString(health.service) || 'platform-backend';
  const status = readString(health.status) || 'unknown';

  return {
    metrics: [
      {
        key: 'runs-total',
        label: '最近运行数',
        value: String(runs.length),
        description: '从运行记录接口直接聚合出的最近运行数量',
        trend: runs.length ? `最近目标：${runs[0].target}` : '暂无运行记录',
      },
      {
        key: 'runs-success',
        label: '成功数',
        value: String(successCount),
        description: '最近这批运行里明确成功的数量',
        trend: failedCount ? `失败/告警 ${failedCount}` : '暂无失败',
      },
      {
        key: 'runs-inflight',
        label: '排队/运行中',
        value: String(inflightCount),
        description: '用于快速判断是否有积压或仍在执行中的任务',
        trend: inflightCount ? '建议优先查看执行结果页' : '当前无积压',
      },
      {
        key: 'backend-live',
        label: '后端状态',
        value: status || 'unknown',
        description: `服务：${service}，环境：${environment}`,
        trend: status === 'ok' ? 'health/live 已连通' : 'health/live 暂未返回正常状态',
      },
    ],
    focusItems: [
      {
        id: 'focus-runs',
        title: failedCount ? '最近运行存在失败/告警' : '最近运行整体稳定',
        owner: '执行中心',
        status: failedCount ? 'attention' : 'stable',
        summary: failedCount
          ? '仪表盘已根据运行列表做聚合，建议进一步在执行结果页查看失败上下文。'
          : '最近运行没有明显失败，当前重点可以转向结构化资产和调度能力。',
      },
      {
        id: 'focus-backend',
        title: '仪表盘接口暂由兼容层拼装',
        owner: '前端适配层',
        status: 'planned',
        summary: '当前优先读取真实 runs / health 接口；等后端补齐 overview 后可直接替换为单接口加载。',
      },
    ],
    recentRuns: runs.slice(0, 5),
  };
};

const loadMockOverview = async (note?: string): Promise<ApiResolvedData<DashboardOverview>> => {
  await wait();
  return {
    data: mockOverview,
    source: 'mock',
    note,
  };
};

export const dashboardApi = {
  /**
   * Dashboard 的加载顺序是：
   * 1. 优先打真实 `/dashboard/overview`
   * 2. 后端没实现该接口时，退到 runs + health/live 兼容聚合
   * 3. 如果后端整体不可用，再退回 mock
   */
  async getOverview(): Promise<ApiResolvedData<DashboardOverview>> {
    if (forceMock) {
      return loadMockOverview('已显式开启 VITE_USE_MOCK=true，当前固定展示 mock 仪表盘。');
    }

    try {
      const payload = await apiClient.get<unknown>('/dashboard/overview');
      const overview = normalizeDashboardOverview(payload);

      if (!overview) {
        throw new Error('仪表盘接口返回结构暂不符合页面要求。');
      }

      return {
        data: overview,
        source: 'api',
      };
    } catch (dashboardError) {
      if (!shouldFallbackToNextLayer(dashboardError)) {
        throw dashboardError;
      }
    }

    try {
      const [runsResult, healthPayload] = await Promise.all([
        managementApi.listRuns({ allowMockFallback: false }),
        apiClient.get<unknown>('/health/live').catch(() => null),
      ]);

      return {
        data: buildCompatibilityOverview(runsResult.data, healthPayload),
        source: 'compatibility',
        note: '后端暂未提供 dashboard/overview，当前由 runs 与 health/live 兼容聚合。',
      };
    } catch (compatibilityError) {
      if (!shouldFallbackToNextLayer(compatibilityError)) {
        throw compatibilityError;
      }
    }

    return loadMockOverview('真实后端暂不可用，当前自动回退为 mock 仪表盘。');
  },
};
