import { apiClient, isApiError } from '@/api/client';
import {
  extractManagementCollection,
  normalizeCaseSummary,
  normalizeEnvironmentDetail,
  normalizeEnvironmentSummary,
  normalizeScheduleSummary,
  normalizeSuiteSummary,
} from '@/api/adapters/management';
import { extractRunCollection, normalizeRunSummary } from '@/api/adapters/runs';
import type {
  ApiResolvedData,
  CaseSummary,
  CreateEnvironmentPayload,
  EnvironmentDetail,
  EnvironmentSummary,
  RunSummary,
  ScheduleSummary,
  SuiteSummary,
  UpdateEnvironmentPayload,
} from '@/types/platform';

/**
 * mock 开关现在只承担“强制 mock”职责：
 * - `true`  : 无论后端是否可用，都直接走 mock
 * - 其他值 : 先尝试真实后端，接口缺失/后端未启动时再回退 mock
 *
 * 这样能保证前端在第二阶段优先贴近真实契约，而不是继续长期活在假数据里。
 */
const forceMock = import.meta.env.VITE_USE_MOCK === 'true';

const wait = (ms = 120) => new Promise((resolve) => window.setTimeout(resolve, ms));

const caseMocks: CaseSummary[] = [
  { id: 'case-001', name: '登录成功', module: '鉴权', method: 'POST', priority: 'P0', status: 'active' },
  { id: 'case-002', name: '获取用户详情', module: '用户中心', method: 'GET', priority: 'P1', status: 'active' },
  { id: 'case-003', name: '修改租户配置', module: '租户管理', method: 'PUT', priority: 'P2', status: 'draft' },
];

const suiteMocks: SuiteSummary[] = [
  { id: 'suite-001', name: '登录冒烟套件', caseCount: 12, lastRun: '今天 09:20', schedule: '工作日 09:00' },
  { id: 'suite-002', name: '核心接口回归', caseCount: 48, lastRun: '昨天 22:00', schedule: '每天 22:00' },
];

const environmentMocks: EnvironmentSummary[] = [
  { id: 'env-001', name: '测试环境', baseUrl: 'https://test.example.com', authMode: 'Token + 租户头', status: 'online' },
  { id: 'env-002', name: '预发环境', baseUrl: 'https://staging.example.com', authMode: 'Cookie + 单点登录', status: 'draft' },
];

const runMocks: RunSummary[] = [
  {
    id: 'run-201',
    name: '支付回归',
    target: 'suite/payment-regression',
    environmentId: 'env-001',
    environmentLabel: '测试环境',
    status: 'failed',
    startedAt: '今天 08:40',
    duration: '11m 02s',
    starter: 'scheduler',
    rawStatus: 'failed',
    note: '失败前已完成鉴权、下单和回调准备步骤。',
    errorSummary: '支付回调断言失败：预期 200，实际返回 502。',
  },
  {
    id: 'run-202',
    name: '用户信息更新',
    target: 'case/user-profile-update',
    environmentId: 'env-002',
    environmentLabel: '预发环境',
    status: 'success',
    startedAt: '今天 10:12',
    duration: '38s',
    starter: '王芳',
    rawStatus: 'succeeded',
    note: '本次回归已通过，接口响应时间稳定在 500ms 以内。',
  },
  {
    id: 'run-203',
    name: '登录链路晨检',
    target: 'suite/login-smoke',
    environmentId: 'env-001',
    environmentLabel: '测试环境',
    status: 'queued',
    startedAt: '今天 10:18',
    duration: '等待调度',
    starter: 'scheduler',
    rawStatus: 'queued',
    note: '任务已进入调度队列，正在等待空闲 worker 拉取。',
  },
  {
    id: 'run-204',
    name: '租户配置巡检',
    target: 'suite/tenant-check',
    environmentId: 'env-002',
    environmentLabel: '预发环境',
    status: 'running',
    startedAt: '今天 10:25',
    duration: '执行中',
    starter: '李明',
    rawStatus: 'running',
    note: '当前正在执行租户切换和配置读取步骤，尚未完成。',
  },
  {
    id: 'run-205',
    name: '跨租户 smoke',
    target: 'suite/cross-tenant-smoke',
    environmentId: 'env-001',
    environmentLabel: '测试环境',
    status: 'warning',
    startedAt: '今天 10:31',
    duration: '2m 14s',
    starter: 'scheduler',
    rawStatus: 'partial_success',
    note: '主流程通过，但有 2 条断言被标记为非阻塞告警。',
  },
];

const scheduleMocks: ScheduleSummary[] = [
  {
    id: 'schedule-001',
    name: '工作日晨检',
    cron: '0 9 * * 1-5',
    target: 'suite/login-smoke',
    environmentId: 'env-001',
    environmentLabel: '测试环境',
    lastRun: '今天 09:00',
    status: 'active',
  },
  {
    id: 'schedule-002',
    name: '夜间回归',
    cron: '0 22 * * *',
    target: 'suite/core-regression',
    environmentId: 'env-002',
    environmentLabel: '预发环境',
    lastRun: '昨天 22:00',
    status: 'paused',
  },
];

const shouldFallbackToMock = (error: unknown) => {
  if (error instanceof TypeError) {
    return true;
  }

  if (!isApiError(error)) {
    return false;
  }

  return [404, 405, 501, 502, 503, 504].includes(error.status);
};

const loadMockCases = async (): Promise<CaseSummary[]> => {
  await wait();
  return caseMocks;
};

const loadMockSuites = async (): Promise<SuiteSummary[]> => {
  await wait();
  return suiteMocks;
};

const loadMockEnvironments = async (): Promise<EnvironmentSummary[]> => {
  await wait();
  return environmentMocks;
};

const loadMockEnvironmentDetail = async (environmentId: string): Promise<EnvironmentDetail> => {
  await wait();
  const matched = environmentMocks.find((item) => item.id === environmentId) ?? environmentMocks[0];
  return {
    ...matched,
    variables: {},
  };
};

const loadMockRuns = async (note?: string): Promise<ApiResolvedData<RunSummary[]>> => {
  await wait();
  return {
    data: runMocks,
    source: 'mock',
    note,
  };
};

const loadMockSchedules = async (): Promise<ScheduleSummary[]> => {
  await wait();
  return scheduleMocks;
};

export const managementApi = {
  async listCases() {
    if (forceMock) {
      return loadMockCases();
    }

    try {
      const payload = await apiClient.get<unknown>('/cases');
      return extractManagementCollection(payload).map((item, index) => normalizeCaseSummary(item, index));
    } catch (error) {
      if (shouldFallbackToMock(error)) {
        return loadMockCases();
      }

      throw error;
    }
  },

  async listSuites() {
    if (forceMock) {
      return loadMockSuites();
    }

    try {
      const payload = await apiClient.get<unknown>('/suites');
      return extractManagementCollection(payload).map((item, index) => normalizeSuiteSummary(item, index));
    } catch (error) {
      if (shouldFallbackToMock(error)) {
        return loadMockSuites();
      }

      throw error;
    }
  },

  async listEnvironments() {
    if (forceMock) {
      return loadMockEnvironments();
    }

    try {
      const payload = await apiClient.get<unknown>('/environments');
      return extractManagementCollection(payload).map((item, index) =>
        normalizeEnvironmentSummary(item, index),
      );
    } catch (error) {
      if (shouldFallbackToMock(error)) {
        return loadMockEnvironments();
      }

      throw error;
    }
  },

  async getEnvironmentDetail(environmentId: string): Promise<EnvironmentDetail> {
    if (forceMock) {
      return loadMockEnvironmentDetail(environmentId);
    }

    try {
      const response = await apiClient.get<unknown>(`/environments/${environmentId}`);
      return normalizeEnvironmentDetail(response, 0);
    } catch (error) {
      if (shouldFallbackToMock(error)) {
        return loadMockEnvironmentDetail(environmentId);
      }

      throw error;
    }
  },

  async createEnvironment(payload: CreateEnvironmentPayload): Promise<EnvironmentDetail> {
    if (forceMock) {
      throw new Error('当前启用了强制 mock，环境写入不会持久化，请关闭 VITE_USE_MOCK 后再试。');
    }

    const response = await apiClient.post<unknown>('/environments', {
      name: payload.name,
      base_url: payload.baseUrl,
      auth_mode: payload.authMode,
      status: payload.status,
    });
    return normalizeEnvironmentDetail(response, 0);
  },

  async updateEnvironment(
    environmentId: string,
    payload: UpdateEnvironmentPayload,
  ): Promise<EnvironmentDetail> {
    if (forceMock) {
      throw new Error('当前启用了强制 mock，环境更新不会持久化，请关闭 VITE_USE_MOCK 后再试。');
    }

    const response = await apiClient.patch<unknown>(`/environments/${environmentId}`, {
      name: payload.name,
      base_url: payload.baseUrl,
      auth_mode: payload.authMode,
      status: payload.status,
    });
    return normalizeEnvironmentDetail(response, 0);
  },

  async deleteEnvironment(environmentId: string): Promise<EnvironmentSummary> {
    if (forceMock) {
      throw new Error('当前启用了强制 mock，环境删除不会持久化，请关闭 VITE_USE_MOCK 后再试。');
    }

    const response = await apiClient.delete<unknown>(`/environments/${environmentId}`);
    return normalizeEnvironmentSummary(response, 0);
  },

  /**
   * Runs 页是第二阶段最先贴近真实后端的页面，所以这里单独做了兼容层：
   * 1. 优先请求真实后端 `/runs`
   * 2. 兼容数组 / 包装对象 / snake_case 字段
   * 3. 如果后端还没补 GET 列表接口，自动回退 mock，让页面仍可工作
   */
  async listRuns(options?: { allowMockFallback?: boolean }): Promise<ApiResolvedData<RunSummary[]>> {
    const allowMockFallback = options?.allowMockFallback ?? true;

    if (forceMock) {
      return loadMockRuns('已显式开启 VITE_USE_MOCK=true，当前固定展示 mock 运行记录。');
    }

    try {
      const payload = await apiClient.get<unknown>('/runs');
      const runs = extractRunCollection(payload).map((item, index) => normalizeRunSummary(item, index));

      return {
        data: runs,
        source: 'api',
      };
    } catch (error) {
      if (!allowMockFallback || !shouldFallbackToMock(error)) {
        throw error;
      }

      return loadMockRuns('真实后端暂未提供可用的运行列表接口，当前自动回退为 mock 数据。');
    }
  },

  async listSchedules() {
    if (forceMock) {
      return loadMockSchedules();
    }

    try {
      const payload = await apiClient.get<unknown>('/schedules');
      return extractManagementCollection(payload).map((item, index) =>
        normalizeScheduleSummary(item, index),
      );
    } catch (error) {
      if (shouldFallbackToMock(error)) {
        return loadMockSchedules();
      }

      throw error;
    }
  },
};
