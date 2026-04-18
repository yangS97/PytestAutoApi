import type {
  CaseSummary,
  EnvironmentDetail,
  EnvironmentSummary,
  ScheduleSummary,
  SuiteSummary,
} from '@/types/platform';

type UnknownRecord = Record<string, unknown>;

const isRecord = (value: unknown): value is UnknownRecord =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const readString = (value: unknown) => (typeof value === 'string' ? value : '');
const readNumber = (value: unknown) => (typeof value === 'number' && Number.isFinite(value) ? value : 0);

export const extractManagementCollection = (payload: unknown): unknown[] => {
  if (Array.isArray(payload)) {
    return payload;
  }

  if (!isRecord(payload)) {
    return [];
  }

  const candidates = ['items', 'data', 'results', 'records', 'list'] as const;
  for (const key of candidates) {
    const value = payload[key];

    if (Array.isArray(value)) {
      return value;
    }
  }

  return [];
};

export const normalizeCaseSummary = (payload: unknown, index: number): CaseSummary => {
  if (!isRecord(payload)) {
    return {
      id: `case-${index}`,
      name: '未命名用例',
      module: '未分类',
      method: 'GET',
      priority: 'P2',
      status: 'draft',
    };
  }

  const method = readString(payload.method).toUpperCase();
  const priority = readString(payload.priority).toUpperCase();
  const status = readString(payload.status).toLowerCase();

  return {
    id: readString(payload.id) || readString(payload.case_id) || `case-${index}`,
    name: readString(payload.name) || readString(payload.title) || '未命名用例',
    module: readString(payload.module) || readString(payload.domain) || '未分类',
    method:
      method === 'GET' || method === 'POST' || method === 'PUT' || method === 'DELETE'
        ? method
        : 'GET',
    priority: priority === 'P0' || priority === 'P1' || priority === 'P2' ? priority : 'P2',
    status: status === 'active' || status === 'draft' ? status : 'draft',
  };
};

export const normalizeSuiteSummary = (payload: unknown, index: number): SuiteSummary => {
  if (!isRecord(payload)) {
    return {
      id: `suite-${index}`,
      name: '未命名套件',
      caseCount: 0,
      lastRun: '尚未执行',
      schedule: '未配置',
    };
  }

  return {
    id: readString(payload.id) || readString(payload.suite_id) || `suite-${index}`,
    name: readString(payload.name) || readString(payload.title) || '未命名套件',
    caseCount: readNumber(payload.caseCount ?? payload.case_count),
    lastRun: readString(payload.lastRun) || readString(payload.last_run) || '尚未执行',
    schedule: readString(payload.schedule) || '未配置',
  };
};

export const normalizeEnvironmentSummary = (
  payload: unknown,
  index: number,
): EnvironmentSummary => {
  if (!isRecord(payload)) {
    return {
      id: `environment-${index}`,
      name: '未命名环境',
      baseUrl: '',
      authMode: '未配置',
      status: 'draft',
    };
  }

  const status = readString(payload.status).toLowerCase();
  return {
    id: readString(payload.id) || readString(payload.environment_id) || `environment-${index}`,
    name: readString(payload.name) || '未命名环境',
    baseUrl: readString(payload.baseUrl) || readString(payload.base_url),
    authMode: readString(payload.authMode) || readString(payload.auth_mode) || '未配置',
    status: status === 'online' || status === 'draft' ? status : 'draft',
  };
};

export const normalizeEnvironmentDetail = (payload: unknown, index: number): EnvironmentDetail => {
  const summary = normalizeEnvironmentSummary(payload, index);
  const variables =
    isRecord(payload) && isRecord(payload.variables)
      ? payload.variables
      : {};

  return {
    ...summary,
    variables,
  };
};

export const normalizeScheduleSummary = (payload: unknown, index: number): ScheduleSummary => {
  if (!isRecord(payload)) {
    return {
      id: `schedule-${index}`,
      name: '未命名任务',
      cron: '',
      target: '未配置目标',
      lastRun: '尚未执行',
      status: 'paused',
    };
  }

  const status = readString(payload.status).toLowerCase();
  return {
    id: readString(payload.id) || readString(payload.schedule_id) || `schedule-${index}`,
    name: readString(payload.name) || '未命名任务',
    cron: readString(payload.cron) || readString(payload.cron_expression),
    target: readString(payload.target) || readString(payload.target_suite_id) || '未配置目标',
    environmentId: readString(payload.environmentId) || readString(payload.environment_id) || undefined,
    environmentLabel:
      readString(payload.environmentLabel) || readString(payload.environment_name) || undefined,
    lastRun: readString(payload.lastRun) || readString(payload.last_run) || '尚未执行',
    status: status === 'active' || status === 'paused' ? status : 'paused',
  };
};
